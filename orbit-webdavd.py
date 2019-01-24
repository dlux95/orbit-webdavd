import io
import re
import logging
import base64
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse
from traceback import print_exc
from time import strftime

from webdavdlib import Lock, SystemdHandler, WriteBuffer
from webdavdlib.exceptions import *
from webdavdlib.filesystems import *

VERSION = "0.1"

class WebDAVServer(ThreadingHTTPServer):
    log = logging.getLogger("WebDAVServer")
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        ThreadingHTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.fs = MultiplexFilesystem(
            {
                "MultiplexTest": DirectoryFilesystem("C:/WebDAVTest/"),
                "Benutzer": DirectoryFilesystem("C:/Users/Daniel/")
            })
        self.locks = {}

    def get_lock(self, uid):
        if uid in self.locks:
            return self.locks[uid]
        else:
            return None

    def set_lock(self, uid, lock):
        self.log.debug("Aquiring Lock on %s" % uid)
        if uid in self.locks:
            raise Exception()
        else:
            self.locks[uid] = lock

    def clear_lock(self, uid):
        self.log.debug("Releasing Lock on %s" % uid)
        if not uid in self.locks:
            raise Exception()
        else:
            del self.locks[uid]


class WebDAVRequestHandler(BaseHTTPRequestHandler):
    worker = 0


    def __init__(self, request, client_address, server):
        self.log = logging.getLogger("WebDAVRequestHandler[%03d]" % WebDAVRequestHandler.worker)
        WebDAVRequestHandler.worker += 1
        WebDAVRequestHandler.worker %= 1000

        self.server_version = "orbit-webdavd/%s" % (VERSION,)

        self.user = None

        BaseHTTPRequestHandler.__init__(self, request, client_address, server)



    def get_depth(self):
        depth = "infinity"
        if self.headers.get("Depth"):
            depth = self.headers.get("Depth")

        if depth == "infinity":
            depth = 10 # Not RFC compliant but performance enhancing
        else:
            depth = int(depth)

        return depth

    def get_destination(self):
        destination = ""
        if self.headers.get("Destination"):
            destination = urlparse(self.headers.get("Destination")).path

        return destination

    def get_data(self):
        data = ""
        if self.headers.get('Content-Length'):
            data = self.rfile.read(int(self.headers.get('Content-Length')))

        return data

    def require_auth(self):
        if self.headers.get('Authorization'):
            base = base64.b64decode(self.headers.get('Authorization').strip("Basic "))
            username, password = base.decode().split(":")
            if username == password: # TODO replace with pam
                self.log.debug("Authentication for %s successful" % username)
                self.user = username
                return False
            else:
                self.log.debug("Authentication for %s failed" % username)

        self.log.debug("Unauthenticated, sending 401")
        self.send_response(401, 'Authorization Required')
        self.send_header('WWW-Authenticate', 'Basic realm="WebDav Auth"')
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', '0')
        self.end_headers()
        return True

    def do_HEAD(self):
        if self.require_auth():
            return

        self.log.info("[%s] HEAD Request on %s" % (self.user, self.path))

        try:
            filedata = self.server.fs.get_content(Path(unquote(self.path)).relative_to("/"))
            b = WriteBuffer(self.wfile)
            b.write(filedata)

            self.log.debug("204 OK")
            self.send_response(204, "OK")
            self.send_header("Content-Length", str(b.getSize()))
            self.end_headers()
        except Exception as e:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_GET(self):
        if self.require_auth():
            return

        self.log.info("[%s] GET Request on %s" % (self.user, self.path))

        try:
            filedata = self.server.fs.get_content(Path(unquote(self.path)).relative_to("/"))
            b = WriteBuffer(self.wfile)
            b.write(filedata)

            self.log.debug("200 OK")
            self.send_response(200, "OK")
            self.send_header("Content-Length", str(b.getSize()))
            self.end_headers()
            b.flush()
        except FileNotFoundError or NoSuchFileException:
            self.log.debug("200 OK")
            self.send_response(404, "Not Found")
            self.end_headers()
        except Exception as e:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_PUT(self):
        if self.require_auth():
            return

        data = self.get_data()
        self.log.info("[%s] PUT Request on %s with length %d" % (self.user, self.path, len(data)))

        try:
            result = self.server.fs.set_content(Path(unquote(self.path)).relative_to("/"), data)

            self.log.debug("204 OK")
            self.send_response(204, "OK")
            self.end_headers()
        except Exception as e:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()


    def do_OPTIONS(self):
        self.log.info("[%s] OPTIONS Request on %s" % (self.user, self.path))

        self.send_response(200, self.server_version)
        self.send_header("Allow", "GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY")
        self.send_header("Content-Length", "0")
        self.send_header("X-Server-Copyright", self.server_version)
        self.send_header("DAV", "1, 2")  # OSX Finder need Ver 2, if Ver 1 -- read only
        self.send_header("MS-Author-Via", "DAV")
        self.end_headers()
        

    def do_PROPFIND(self):
        if self.require_auth():
            return

        data = self.get_data()
        depth = self.get_depth()
        self.log.info("[%s] PROPFIND Request on %s with depth %d and length %d" % (self.user, self.path, depth, len(data)))

        try:
            resqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            resdata = {}

            depthqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            while depth > 0:
                cpqueue = depthqueue.copy()
                for res in cpqueue:
                    workingres = Path(unquote(res))
                    for sub in self.server.fs.get_children(workingres):
                        resqueue.append(sub)
                        depthqueue.append(sub)
                depth = depth-1

            for resource in resqueue:
                workingres = Path(unquote(resource))
                resdata[workingres] = self.server.fs.get_props(workingres)

            w = WriteBuffer(self.wfile)
            w.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n")
            w.write("<D:multistatus xmlns:D=\"DAV:\" xmlns:Z=\"urn:schemas-microsoft-com:\"   xmlns:Office=\"urn:schemas-microsoft-com:office:office\">\n")


            for res, props in resdata.items():
                w.write("<D:response>\n")
                w.write("<D:href>/%s</D:href>\n" % (res.as_posix().strip("."),))
                w.write("<D:propstat>\n")
                w.write("<D:prop>\n")
                propcount = 0
                for propname, propvalue in props.items():
                    if propname == "D:status":
                        continue

                    propcount = propcount + 1
                    if propvalue is True or propvalue is False:
                        if propvalue is True:
                            w.write("<%s/>\n" % (propname,))
                    else:
                        w.write("<%s>%s</%s>\n" % (propname, propvalue, propname))

                if propcount > 0:
                    uid = self.server.fs.get_uid(workingres)
                    if server.get_lock(uid) is None:
                        w.write("<D:supportedlock>\n")
                        w.write("<D:lockentry>\n")
                        w.write("<D:lockscope><D:exclusive/></D:lockscope>\n")
                        w.write("<D:locktype><D:write/></D:locktype>\n")
                        w.write("</D:lockentry>\n")
                        w.write("</D:supportedlock>\n")
                    else:
                        lock = server.get_lock(uid)
                        w.write("<D:lockdiscovery>\n")
                        w.write("<D:activelock>\n")
                        w.write("<D:locktype><D:write/></D:locktype>\n")
                        w.write("<D:lockscope><D:%s/></D:lockscope>\n" % lock.mode)
                        w.write("<D:depth>%s</D:depth>\n" % lock.depth)
                        w.write("<D:owner>%s</D:owner>\n" % lock.owner)
                        w.write("<D:timeout>%s</D:timeout>\n" % lock.timeout)
                        w.write("<D:locktoken><D:href>opaquelocktoken:%s</D:href></D:locktoken>" % lock.token)
                        w.write("</D:lockdiscovery>\n")
                        w.write("</D:activelock>\n")

                w.write("</D:prop>\n")
                w.write("<D:status>HTTP/1.1 %s</D:status>\n" % props["D:status"])
                w.write("</D:propstat>\n")
                w.write("</D:response>\n")
            w.write("</D:multistatus>\n")

            self.log.debug("207 Multi-Status")
            self.send_response(207, "Multi-Status")  # Multi-Status
            self.send_header("Content-Type", "text/xml")
            self.send_header("Charset", "utf-8")
            self.send_header("Content-Length", str(w.getSize()))
            self.end_headers()
            w.flush()
            
        except NoSuchFileException:
            self.log.debug("404 Not Found")
            self.send_response(404, "Not Found")  # Multi-Status
            self.end_headers()
            
        except Exception:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()
            


    def do_DELETE(self):
        if self.require_auth():
            return

        self.log.info("[%s] DELETE Request on %s" % (self.user, self.path))

        try:
            self.server.fs.delete(Path(unquote(self.path)).relative_to("/"))

            self.log.debug("204 OK")
            self.send_response(204, "OK")
            self.end_headers()
            
        except Exception as e:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()
            

    def do_MKCOL(self):
        if self.require_auth():
            return

        data = self.get_data()
        self.log.info("[%s] MKCOL Request on %s with length %d" % (self.user, self.path, len(data)))

        try:
            self.server.fs.create(Path(unquote(self.path)).relative_to("/"), dir=True)

            self.log.debug("201 Created")
            self.send_response(201, "Created")
            self.end_headers()
            
        except Exception as e:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()
            

    def do_MOVE(self):
        if self.require_auth():
            return

        destination = self.get_destination()
        self.log.info("[%s] MOVE Request on %s to %s" % (self.user, self.path, destination))

        # TODO Implement
        

    def do_COPY(self):
        if self.require_auth():
            return

        destination = self.get_destination()
        self.log.info("[%s] COPY Request on %s to %s" % (self.user, self.path, destination))

        # TODO Implement
        

    def do_LOCK(self):
        if self.require_auth():
            return

        data = self.get_data()
        self.log.info("[%s] LOCK Request on %s with length %d" % (self.user, self.path, len(data)))

        lockowner = None
        if data != "":
            lockowner = re.search("<D:href>(.*)</D:href>", str(data)).group(1)

        if not lockowner == None:
            uid = self.server.fs.get_uid(Path(unquote(self.path)).relative_to("/"))
            lock = server.get_lock(uid)
            if lock == None:
                lock = Lock(uid, lockowner, "exclusive", "infinity", "Second-300")
                server.set_lock(uid, lock)
                w = WriteBuffer(self.wfile)
                w.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>")
                w.write("<D:prop xmlns:D=\"DAV:\">")
                w.write("<D:lockdiscovery>")
                w.write("<D:activelock>")
                w.write("<D:locktype><D:write/></D:locktype>")
                w.write("<D:lockscope><D:%s/></D:lockscope>" % lock.mode)
                w.write("<D:depth>%s</D:depth>" % lock.depth)
                w.write("<D:owner>")
                w.write("<D:href>%s</D:href>" % lock.owner)
                w.write("</D:owner>")
                w.write("<D:timeout>%s</D:timeout>" % lock.timeout)
                w.write("<D:locktoken><D:href>opaquelocktoken:%s</D:href></D:locktoken>" % lock.token)
                w.write("</D:activelock>")
                w.write("</D:lockdiscovery>")
                w.write("</D:prop>")

                self.log.debug("200 OK")
                self.send_response(200, "OK")
                self.send_header("Lock-Token", "<opaquelocktoken:%s>" % lock.token)
                self.send_header("Content-type", 'text/xml')
                self.send_header("Charset", '"utf-8"')
                self.send_header("Content-Length", str(w.getSize()))
                self.end_headers()

                w.flush()
                
            else:
                self.log.debug("409 Conflict")
                self.send_response(409, "Conflict")
                self.send_header("Content-Length", 0)
                self.end_headers()
                

    def do_UNLOCK(self):
        if self.require_auth():
            return

        data = self.get_data()
        self.log.info("[%s] UNLOCK Request on %s with length %d" % (self.user, self.path, len(data)))

        locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["Lock-Token"])).group(1)

        uid = self.server.fs.get_uid(Path(unquote(self.path)).relative_to("/"))

        if not server.get_lock(uid) is None:
            lock = server.get_lock(uid)
            if lock.token == locktoken:
                server.clear_lock(uid)

                self.log.debug("200 OK")
                self.send_response("200 OK")
                self.send_header("Content-Length", 0)
                self.end_headers()
            else:
                # TODO search right status code
                self.log.debug("405 Method not allowed")
                self.send_response("405 Method not allowed")
                self.send_header("Content-Length", 0)
                self.end_headers()
        

    def log_message(self, format, *args):
        pass




if __name__ == "__main__":
    root_logger = logging.getLogger()
    root_logger.setLevel("DEBUG")
    root_logger.addHandler(SystemdHandler())

    server = WebDAVServer(("", 8080), WebDAVRequestHandler)
    server.serve_forever()
