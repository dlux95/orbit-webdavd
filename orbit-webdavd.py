import http.server
import io
import re
from webdavdlib.exceptions import *
from webdavdlib.filesystems import *
from pathlib import Path
from urllib.parse import unquote, urlparse
from traceback import print_exc


VERSION = "0.1"

class WriteBuffer:
    def __init__(self, w):
        self.w = w
        self.buf = io.BytesIO()

    def write(self, s):

        if isinstance(s, str):
            self.buf.write(s.encode("utf-8"))  # add unicode(s,'utf-8') for chinese code.
        else:
            self.buf.write(s)
    def flush(self):
        self.w.write(self.buf.getvalue())
        self.w.flush()

    def getSize(self):
        return len(self.buf.getvalue())

class WebDAVServer(http.server.ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        http.server.ThreadingHTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)

        self.locks = {}

    def get_lock(self, uid):
        if uid in self.locks:
            return self.locks[uid]
        else:
            return None

    def set_lock(self, uid, lock):
        if uid in self.locks:
            raise Exception()
        else:
            self.locks[uid] = lock

    def clear_lock(self, uid):
        if uid in self.locks:
            raise Exception()
        else:
            del self.locks[uid]


class WebDAVRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.server_version = "orbit-webdavd/%s" % (VERSION,)
        self.fs = MultiplexFilesystem(
            {
                "MultiplexTest" : DirectoryFilesystem("C:/WebDAVTest/"),
                "Benutzer": DirectoryFilesystem("C:/Users/Daniel/")
             })
        self.close_connection = False
        self.protocol_version = "HTTP/1.1"

        http.server.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

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

    def do_HEAD(self):
        print("HEAD ", self.path)

        try:
            filedata = self.fs.get_content(Path(unquote(self.path)).relative_to("/"))
            b = WriteBuffer(self.wfile)
            b.write(filedata)

            print("204 OK")
            self.send_response(204, "OK")
            self.send_header("Content-Length", str(b.getSize()))
            self.end_headers()
        except Exception as e:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_GET(self):
        print("GET ", self.path)

        try:
            filedata = self.fs.get_content(Path(unquote(self.path)).relative_to("/"))
            b = WriteBuffer(self.wfile)
            b.write(filedata)

            print("200 OK")
            self.send_response(200, "OK")
            self.send_header("Content-Length", str(b.getSize()))
            self.end_headers()
            b.flush()
        except FileNotFoundError:
            print("404 Not Found")
            self.send_response(404, "Not Found")
            self.end_headers()
        except Exception as e:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_PUT(self):
        data = self.get_data()
        print(self.request_version, " PUT ", self.path, " Data:", len(data))

        try:
            result = self.fs.set_content(Path(unquote(self.path)).relative_to("/"), data)

            print("204 OK")
            self.send_response(204, "OK")
            self.end_headers()
        except Exception as e:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()


    def do_OPTIONS(self):
        request = webdavdlib.WebDAVRequest(self.headers, self.get_data())
        print(self.request_version, " OPTIONS ", self.path)
        self.send_response(200, self.server_version)
        self.send_header("Allow", "GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY")
        self.send_header("Content-Length", "0")
        self.send_header("X-Server-Copyright", self.server_version)
        self.send_header("DAV", "1, 2")  # OSX Finder need Ver 2, if Ver 1 -- read only
        self.send_header("MS-Author-Via", "DAV")
        self.end_headers()

    def do_PROPFIND(self):
        data = self.get_data()
        depth = self.get_depth()
        print(self.request_version, " PROPFIND ", self.path, " Depth: ", depth, " Data:", len(data))

        try:
            resqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            resdata = {}

            depthqueue = [Path(unquote(self.path)).relative_to("/").as_posix()]
            while depth > 0:
                cpqueue = depthqueue.copy()
                for res in cpqueue:
                    workingres = Path(unquote(res))
                    for sub in self.fs.get_children(workingres):
                        resqueue.append(sub)
                        depthqueue.append(sub)
                depth = depth-1

            for resource in resqueue:
                workingres = Path(unquote(resource))
                resdata[workingres] = self.fs.get_props(workingres)

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
                    w.write("<D:supportedlock>\n")
                    w.write("<D:lockentry>\n")
                    w.write("<D:lockscope><D:exclusive/></D:lockscope>\n")
                    w.write("<D:locktype><D:write/></D:locktype>\n")
                    w.write("</D:lockentry>\n")
                    w.write("</D:supportedlock>\n")
                w.write("</D:prop>\n")
                w.write("<D:status>HTTP/1.1 %s</D:status>\n" % props["D:status"])
                w.write("</D:propstat>\n")
                w.write("</D:response>\n")
            w.write("</D:multistatus>\n")

            print("207 Multi-Status")
            self.send_response(207, "Multi-Status")  # Multi-Status
            self.send_header("Content-Type", "text/xml")
            self.send_header("Charset", "utf-8")
            self.send_header("Content-Length", str(w.getSize()))
            self.end_headers()
            w.flush()
        except NoSuchFileException:
            print("404 Not Found")
            self.send_response(404, "Not Found")  # Multi-Status
            self.end_headers()
        except Exception:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()


    def do_DELETE(self):
        print(self.request_version, " DELETE ", self.path)

        try:
            self.fs.delete(Path(unquote(self.path)).relative_to("/"))

            print("204 OK")
            self.send_response(204, "OK")
            self.end_headers()
        except Exception as e:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_MKCOL(self):
        data = self.get_data()
        print(self.request_version, " MKCOL ", self.path, " Data:", len(data))

        try:
            self.fs.create(Path(unquote(self.path)).relative_to("/"), dir=True)

            print("201 Created")
            self.send_response(201, "Created")
            self.end_headers()
        except Exception as e:
            print_exc()
            print("500 Server Error")
            self.send_response(500, "Server Error")
            self.end_headers()

    def do_MOVE(self):
        destination = self.get_destination()
        print(self.request_version, " MOVE ", self.path, " to ", destination)

        result = self.fs.move(Path(unquote(self.path)).relative_to("/"), Path(unquote(destination)).relative_to("/"))

        self.send_response(result.get_code(), result.get_name())
        self.end_headers()

    def do_COPY(self):
        destination = self.get_destination()
        print(self.request_version, " MOVE ", self.path, " to ", destination)

        result = self.fs.copy(Path(unquote(self.path)).relative_to("/"),
                              Path(unquote(destination)).relative_to("/"))

        self.send_response(result.get_code(), result.get_name())
        self.end_headers()

    def do_LOCK(self):
        data = self.get_data()
        print(self.request_version, " LOCK ", self.path, " Data:", len(data))
        lockowner = None
        if data != "":
            lockowner = re.search("<D:href>(.*)</D:href>", str(data)).group(1)

        result = self.fs.lock(Path(unquote(self.path)).relative_to("/"), lockowner)

        if result.get_data() != None:
            w = WriteBuffer(self.wfile)
            w.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>")
            w.write("<D:prop xmlns:D=\"DAV:\">")
            w.write("<D:lockdiscovery>")
            w.write("<D:activelock>")
            w.write("<D:locktype><D:write/></D:locktype>")
            w.write("<D:lockscope><D:exclusive/></D:lockscope>")
            w.write("<D:depth>Infinity</D:depth>")
            w.write("<D:owner>")
            w.write("<D:href>" + str(lockowner) + "</D:href>")
            w.write("</D:owner>")
            w.write("<D:timeout>Infinite</D:timeout>")
            w.write("<D:locktoken><D:href>opaquelocktoken:" + result.get_data()[0] + "</D:href></D:locktoken>")
            w.write("</D:activelock>")
            w.write("</D:lockdiscovery>")
            w.write("</D:prop>")

        self.send_response(result.get_code(), result.get_name())
        if result.get_data() != None:
            self.send_header("Lock-Token", "<opaquelocktoken:" + result.get_data()[0] + ">")
            self.send_header("Content-type", 'text/xml')
            self.send_header("Charset", '"utf-8"')
            self.send_header("Content-Length", str(w.getSize()))
        else:
            self.send_header("Content-Length", 0)
        self.end_headers()

        if result.get_data() != None:
            w.flush()

    def do_UNLOCK(self):
        data = self.get_data()
        print(self.request_version, " UNLOCK ", self.path, "Data:", len(data))

        locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["Lock-Token"])).group(1)

        result = self.fs.unlock(Path(unquote(self.path)).relative_to("/"), locktoken)

        self.send_response(result.get_code(), result.get_name())
        self.send_header("Content-Length", 0)
        self.end_headers()

    def log_message(self, format, *args):
        pass




if __name__ == "__main__":
    server = WebDAVServer(("", 8080), WebDAVRequestHandler)
    server.serve_forever()
