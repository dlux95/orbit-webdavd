import io
import re
import logging
import base64
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse
from traceback import print_exc
from time import strftime
from functools import lru_cache

from webdavdlib import Lock, SystemdHandler, WriteBuffer, get_template
from webdavdlib.exceptions import *
from webdavdlib.filesystems import *
from webdavdlib.requests import *

from configuration import *


VERSION = "v0.2"

class WebDAVServer(HTTPServer):
    log = logging.getLogger("WebDAVServer")
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        ThreadingHTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.fs = config_filesystems()

        self.authenticator = config_authenticator()

        self.templates = {
            "lock" : get_template("webdavdlib/templates/lock.template.jinja2"),
            "propfind" : get_template("webdavdlib/templates/propfind.template.jinja2")
        }
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
            depth = 32  # Not RFC compliant but performance enhancing
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

    def require_auth(self, request):
        if request.username and request.password and self.server.authenticator.authenticate(request.username, request.password):
            self.user = request.username
            return False

        self.log.debug("Unauthenticated, sending 401")
        self.send_response(401, 'Authorization Required')
        self.send_header('WWW-Authenticate', 'Basic realm="WebDav Auth"')
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-length', '0')
        self.end_headers()
        return True

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except:
            self.log.exception("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_HEAD(self):
        request = HEADRequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] HEAD Request on %s" % (self.user, self.path))



        filedata = self.server.fs.get_content(self.user, Path(request.path).relative_to("/"))
        b = WriteBuffer(self.wfile)
        b.write(filedata)

        self.log.debug("204 OK ("+str(b.getSize())+")")
        self.send_response(204, "OK")
        self.send_header("Content-Length", str(b.getSize()))
        self.end_headers()

    def do_GET(self):
        request = GETRequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] GET Request on %s" % (self.user, self.path))


        try:
            props = self.server.fs.get_props(self.user, Path(request.path).relative_to("/"), ["D:iscollection"])
            if props["D:iscollection"]:

                children = self.server.fs.get_children(self.user, Path(request.path).relative_to("/"))

                b = WriteBuffer(self.wfile)
                b.write(str(children))
                
                self.log.debug("200 OK")
                self.send_response(200, "OK")
                self.send_header("Content-Length", str(b.getSize()))
                self.end_headers()
                b.flush()
            else:
                filedata = self.server.fs.get_content(self.user, Path(request.path).relative_to("/"))
                b = WriteBuffer(self.wfile)
                b.write(filedata)

                self.log.debug("200 OK")
                self.send_response(200, "OK")
                self.send_header("Content-Length", str(b.getSize()))
                self.end_headers()
                b.flush()
        except FileNotFoundError or NoSuchFileException:
            self.log.debug("404 Not Found")
            self.send_response(404, "Not Found")
            self.end_headers()
        except PermissionError:
            self.log.debug("403 Forbidden")
            self.send_response(403, "Forbidden")
            self.end_headers()

    def do_PUT(self):
        request = PUTRequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] PUT Request on %s with length %d" % (self.user, self.path, len(request.data)))

        exists = True
        try:
            self.server.fs.get_props(self.user, Path(request.path).relative_to("/"))
        except NoSuchFileException:
            exists = False

        result = self.server.fs.set_content(self.user, Path(request.path).relative_to("/"), request.data)

        if exists:
            self.log.debug("204 No-Content")
            self.send_response(204, "No-Content")
            self.send_header('Content-length', '0')
            self.end_headers()
        else:
            self.log.debug("201 Created")
            self.send_response(201, "Created")
            self.send_header('Content-length', '0')
            self.end_headers()


    def do_OPTIONS(self):
        self.log.info("[%s] OPTIONS Request on %s" % (self.user, self.path))

        self.send_response(200, self.server_version)
        self.send_header("Allow", "GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY")
        self.send_header("Content-Length", "0")
        self.send_header("X-Server-Copyright", self.server_version)
        self.send_header("DAV", "1, 2")  # OSX Finder need Ver 2, if Ver 1 -- read only
        self.send_header("MS-Author-Via", "DAV")
        self.send_header('WWW-Authenticate', 'Basic realm="WebDav Auth"')
        self.end_headers()
        

    def do_PROPFIND(self):
        request = PROPFINDRequest(self)
        if self.require_auth(request):
            return

        data = request.data
        depth = request.depth
        self.log.info("[%s] PROPFIND Request on %s with depth %s and length %d" % (self.user, self.path, depth, len(data)))
        try:
            resqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            resdata = {}

            depthqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            while depth > 0:
                cpqueue = depthqueue.copy()
                for res in cpqueue:
                    workingres = Path(unquote(res))
                    for sub in self.server.fs.get_children(self.user, workingres):
                        resqueue.append(sub)
                        depthqueue.append(sub)
                depth = depth-1

            for resource in resqueue:
                workingres = Path(unquote(resource))
                resdata[workingres] = self.server.fs.get_props(self.user, workingres)
                resdata[workingres]["lock"] = self.server.get_lock(self.server.fs.get_uid(self.user, workingres))

            w = WriteBuffer(self.wfile)
            w.write(self.server.templates["propfind"].render(resdata=resdata))

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
        except PermissionError:
            self.log.debug("403 Forbidden")
            self.send_response(403, "Forbidden")
            self.end_headers()

    def do_DELETE(self):
        request = DELETERequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] DELETE Request on %s" % (self.user, self.path))

        uid = self.server.fs.get_uid(self.user, Path(unquote(self.path)).relative_to("/"))
        lock = server.get_lock(uid)

        if lock != None:
            try:
                locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["If"])).group(1)

                if lock.token == locktoken:
                    self.server.fs.delete(self.user, Path(unquote(self.path)).relative_to("/"))
                    server.clear_lock(uid)
                else:
                    # TODO search right status code
                    self.log.debug("423 Locked")
                    self.send_response(423, "Locked")
                    self.end_headers()
                    return
            except:
                self.log.debug("No locktoken")
                self.log.debug("423 Locked")
                self.send_response(423, "Locked")
                self.end_headers()
                return
        else:
            self.server.fs.delete(self.user, Path(unquote(self.path)).relative_to("/"))

        self.log.debug("204 OK")
        self.send_response(204, "OK")
        self.end_headers()

    def do_MKCOL(self):
        request = MKCOLRequest(self)
        if self.require_auth(request):
            return


        self.log.info("[%s] MKCOL Request on %s with length %d" % (self.user, self.path, len(request.data)))

        self.server.fs.create(self.user, Path(request.path).relative_to("/"), dir=True)

        self.log.debug("201 Created")
        self.send_response(201, "Created")
        self.end_headers()

    def do_PROPPATCH(self):
        request = PROPPATCHRequest(self)
        if self.require_auth(request):
            return

        #data = self.get_data()
        #self.log.info("[%s] PROPPATCH Request on %s with length %d" % (self.user, self.path, len(data)))

        self.do_PROPFIND()

            

    def do_MOVE(self):
        request = MOVERequest(self)
        if self.require_auth(request):
            return


        self.log.info("[%s] MOVE Request on %s to %s" % (self.user, request.path, request.destination))

        if (self.server.fs.get_props(self.user, Path(request.path).relative_to("/"), ["D:iscollection"])[
            "D:iscollection"]):
            copyqueue = [self.path]

            while len(copyqueue) > 0:
                element = copyqueue.pop()
                self.log.debug("Copy Element " + element)
                children = self.server.fs.get_children(self.user, Path(request.path).relative_to("/"))
                for c in children:
                    copyqueue.append(c)
        else:
            exists = True
            try:
                self.server.fs.get_props(self.user, Path(request.destination).relative_to("/"))
            except NoSuchFileException:
                exists = False

                self.server.fs.set_content(self.user, Path(request.destination).relative_to("/"),
                                           self.server.fs.get_content(self.user,
                                                                      Path(request.path).relative_to("/")))
                self.server.fs.delete(self.user, Path(request.path).relative_to("/"))

            if exists:
                self.log.debug("204 No-Content")
                self.send_response(204, "No-Content")
                self.send_header('Content-length', '0')
                self.end_headers()
            else:
                self.log.debug("201 Created")
                self.send_response(201, "Created")
                self.send_header('Content-length', '0')
                self.end_headers()


    def do_COPY(self):
        request = COPYRequest(self)
        if self.require_auth(request):
            return

        destination = self.get_destination()
        self.log.info("[%s] COPY Request on %s to %s" % (self.user, self.path, destination))


        if(self.server.fs.get_props(self.user, Path(unquote(self.path)).relative_to("/"), ["D:iscollection"])["D:iscollection"]):
            copyqueue = [self.path]

            while len(copyqueue) > 0:
                element = copyqueue.pop()
                self.log.debug("Copy Element " + element)
                children = self.server.fs.get_children(self.user, Path(unquote(self.path)).relative_to("/"))
                for c in children:
                    copyqueue.append(c)
        else:
            exists = True
            try:
                self.server.fs.get_props(self.user, Path(unquote(destination)).relative_to("/"))
            except NoSuchFileException:
                exists = False

                self.server.fs.set_content(self.user, Path(unquote(destination)).relative_to("/"),
                                           self.server.fs.get_content(self.user,
                                                                      Path(unquote(self.path)).relative_to("/")))

            if exists:
                self.log.debug("204 No-Content")
                self.send_response(204, "No-Content")
                self.send_header('Content-length', '0')
                self.end_headers()
            else:
                self.log.debug("201 Created")
                self.send_response(201, "Created")
                self.send_header('Content-length', '0')
                self.end_headers()
        

    def do_LOCK(self):
        request = LOCKRequest(self)
        if self.require_auth(request):
            return

        data = request.data
        self.log.info("[%s] LOCK Request on %s with length %d" % (self.user, self.path, len(data)))


        try:
            self.server.fs.get_props(self.user, Path(unquote(self.path)).relative_to("/"))
        except NoSuchFileException:
            uid = self.server.fs.get_uid(self.user, Path(unquote(self.path)).relative_to("/"))
            lock = Lock(uid, request.lockowner, "exclusive", "infinity", "Second-300")
            self.server.set_lock(uid, lock)
            w = WriteBuffer(self.wfile)
            w.write(self.server.templates["lock"].render(lock=lock))
 
            self.log.debug("404 Not Found")
            self.send_response(404, "Not Found")
            self.send_header("Lock-Token", "<opaquelocktoken:%s>" % lock.token)
            self.send_header("Content-type", 'text/xml')
            self.send_header("Charset", '"utf-8"')
            self.send_header("Content-Length", str(w.getSize()))
            self.end_headers()

            w.flush()
            return            

        uid = self.server.fs.get_uid(self.user, Path(unquote(self.path)).relative_to("/"))
        lock = server.get_lock(uid)
        if lock == None:
            lock = Lock(uid, request.lockowner, "exclusive", "infinity", "Second-300")
            self.server.set_lock(uid, lock)
            w = WriteBuffer(self.wfile)
            w.write(self.server.templates["lock"].render(lock=lock))

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
        request = UNLOCKRequest(self)
        if self.require_auth(request):
            return

        data = request.data
        self.log.info("[%s] UNLOCK Request on %s with length %d" % (self.user, self.path, len(data)))

        locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["Lock-Token"])).group(1)

        uid = self.server.fs.get_uid(self.user, Path(unquote(self.path)).relative_to("/"))

        if not server.get_lock(uid) is None:
            lock = server.get_lock(uid)
            if lock.token == locktoken:
                server.clear_lock(uid)

                self.log.debug("200 OK")
                self.send_response(200, "OK")
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
    root_logger.setLevel(config_loglevel())
    root_logger.addHandler(SystemdHandler())

    server = WebDAVServer(("", config_port()), WebDAVRequestHandler)
    server.serve_forever()
