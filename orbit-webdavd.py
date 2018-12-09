import http.server
import io
import sys
import webdavdlib.filesystems
from webdavdlib.properties import *
import pathlib
import urllib.parse
from webdavdlib.exceptions import *

VERSION = "0.1"

class WriteBuffer:
    def __init__(self, w, debug=True):
        self.w = w
        self.buf = io.StringIO('')
        self.debug = debug

    def write(self, s):
        if self.debug:
            sys.stdout.write("\t" + s)
        self.buf.write(s)  # add unicode(s,'utf-8') for chinese code.

    def flush(self):
        self.w.write(self.buf.getvalue().encode("utf-8"))
        self.w.flush()

    def getSize(self):
        return len(self.buf.getvalue().encode("utf-8"))

class WebDAVServer(http.server.ThreadingHTTPServer):
    pass


class WebDAVRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.server_version = "orbit-webdavd/%s" % (VERSION,)
        self.fs = webdavdlib.filesystems.DirectoryFilesystem("C:/WebDAVTest/")
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
            destination = urllib.parse.urlparse(self.headers.get("Destination")).path

        return destination

    def get_data(self):
        data = ""
        if self.headers.get('Content-Length'):
            data = self.rfile.read(int(self.headers.get('Content-Length')))

        return data

    def do_HEAD(self):
        print("HEAD ", self.path)

        resdata = self.fs.get(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"))

        self.send_response(resdata.get_code(), resdata.get_name())
        if not resdata.get_data() == None:
            self.send_header("Content-Length", str(len(resdata.get_data())))

        self.end_headers()

    def do_GET(self):
        print("GET ", self.path)

        resdata = self.fs.get(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"))

        self.send_response(resdata.get_code(), resdata.get_name())
        if not resdata.get_data() == None:
            self.send_header("Content-Length", str(len(resdata.get_data())))

        self.end_headers()

        if not resdata.get_data() == None:
            self.wfile.write(resdata.get_data())



    def do_OPTIONS(self):
        print(self.request_version, " OPTIONS ", self.path)
        self.send_response(200, self.server_version)
        self.send_header("Allow", "GET, HEAD, POST, PUT, DELETE, OPTIONS, PROPFIND, PROPPATCH, MKCOL, LOCK, UNLOCK, MOVE, COPY")
        self.send_header("Content-Length", "0")
        self.send_header("X-Server-Copyright", self.server_version)
        self.send_header("DAV", "1, 2")  # OSX Finder need Ver 2, if Ver 1 -- read only
        self.send_header("MS-Author-Via", "DAV")
        self.end_headers()

    def do_PROPFIND(self):
        depth = self.get_depth()
        data = self.get_data()

        print(self.request_version, " PROPFIND ", self.path, " Depth: ", depth, " Data:", len(data))

        w = WriteBuffer(self.wfile, False)
        w.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\r\n")
        w.write("<D:multistatus xmlns:D=\"DAV:\" xmlns:Z=\"urn:schemas-microsoft-com:\">\r\n")

        result = self.fs.propfind(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"), depth, [])
        resultlist = result.get_data()
        if not resultlist == None:
            if not isinstance(resultlist, list):
                resultlist = [resultlist]

            for res in resultlist:
                w.write("<D:response>\n")
                w.write("<D:href>%s</D:href>\n" % res.get_property(HrefProperty).get_value())
                w.write("<D:propstat>\n")
                w.write("<D:prop>\n")
                for p in res._properties:
                    if isinstance(p, HrefProperty):
                        continue
                    w.write(p.to_xml())

                w.write("</D:prop>\n")
                w.write("<D:status>HTTP/1.1 200 OK</D:status>\n")
                w.write("</D:propstat>\n")
                w.write("</D:response>\n")
        w.write("</D:multistatus>\r\n")

        self.send_response(result.get_code(), result.get_name())  # Multi-Status
        self.send_header("Content-Type", "text/xml")
        self.send_header("Charset", "utf-8")
        self.send_header("Content-Length", str(w.getSize()))
        self.end_headers()
        w.flush()



    def do_DELETE(self):
        print(self.request_version, " DELETE ", self.path)
        pass

    def do_MKCOL(self):
        data = self.get_data()
        print(self.request_version, " MKCOL ", self.path, " Data:", len(data))

        result = self.fs.mkcol(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"))

        self.send_response(result.get_code(), result.get_name())
        self.end_headers()

    def do_MOVE(self):
        destination = self.get_destination()
        print(self.request_version, " MOVE ", self.path, " to ", destination)

        result = self.fs.move(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"), pathlib.Path(urllib.parse.unquote(destination)).relative_to("/"))

        self.send_response(result.get_code(), result.get_name())
        self.end_headers()

    def do_COPY(self):
        print(self.request_version, " COPY ", self.path)
        pass

    def do_LOCK(self):
        print(self.request_version, " LOCK ", self.path)
        pass

    def do_UNLOCK(self):
        print(self.request_version, " UNLOCK ", self.path)
        pass

    def do_PUT(self):
        data = self.get_data()
        print(self.request_version, " PUT ", self.path)

        result = self.fs.put(pathlib.Path(urllib.parse.unquote(self.path)).relative_to("/"), data)

        self.send_response(result.get_code(), result.get_name())
        self.end_headers()


    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = WebDAVServer(("", 8080), WebDAVRequestHandler)
    server.serve_forever()
