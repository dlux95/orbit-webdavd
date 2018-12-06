import http.server
import io
import sys
import webdavdlib.filesystems
from webdavdlib.properties import *
import pathlib

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

    def get_data(self):
        data = ""
        if self.headers.get('Content-Length'):
            data = self.rfile.read(int(self.headers.get('Content-Length')))

        return data

    def do_HEAD(self):
        print("HEAD ", self.path)
        pass

    def do_GET(self):
        print("GET ", self.path)

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

        result = self.fs.get_resources(pathlib.Path(self.path).relative_to("/"), depth, [])
        if result:
            if not isinstance(result, list):
                result = [result]

            for res in result:
                print(res)
                w.write("<D:response>\n")
                w.write("<D:href>%s</D:href>\n" % res.get_property(HrefProperty).get_value())
                w.write("<D:propstat>\n")
                w.write("<D:prop>\n")
                for p in res._properties:
                    if isinstance(p, HrefProperty):
                        continue
                    w.write(p.to_xml())

                w.write("""<D:supportedlock>
                <D:lockentry>
                <D:lockscope><D:exclusive/></D:lockscope>
                <D:locktype><D:write/></D:locktype>
                </D:lockentry>
                <D:lockentry>
                <D:lockscope><D:shared/></D:lockscope>
                <D:locktype><D:write/></D:locktype>
                </D:lockentry>
                </D:supportedlock>
                <D:lockdiscovery/>
                """)

                w.write("</D:prop>\n")
                w.write("<D:status>HTTP/1.1 200 OK</D:status>\n")
                w.write("</D:propstat>\n")
                w.write("</D:response>\n")
        # w.write("""
        # <D:response>
        # <D:href>/</D:href>
        # <D:propstat>
        # <D:prop>
        # <D:resourcetype><D:collection/></D:resourcetype>
        # <D:creationdate>2018-12-03T12:20:56Z</D:creationdate>
        # <D:getlastmodified>Mon, 03 Dec 2018 12:20:56 GMT</D:getlastmodified>
        # <D:getetag>"1000-57c1d2e50e5b2"</D:getetag>
        # <D:supportedlock>
        # <D:lockentry>
        # <D:lockscope><D:exclusive/></D:lockscope>
        # <D:locktype><D:write/></D:locktype>
        # </D:lockentry>
        # <D:lockentry>
        # <D:lockscope><D:shared/></D:lockscope>
        # <D:locktype><D:write/></D:locktype>
        # </D:lockentry>
        # </D:supportedlock>
        # <D:lockdiscovery/>
        # </D:prop>
        # <D:status>HTTP/1.1 200 OK</D:status>
        # </D:propstat>
        # </D:response>
        # """)


        w.write("</D:multistatus>\r\n")

        self.send_response(207, "Multi-Status")  # Multi-Status
        self.send_header("Content-Type", "text/xml")
        self.send_header("Charset", "utf-8")
        self.send_header("Content-Length", str(w.getSize()))
        self.end_headers()
        w.flush()



    def do_DELETE(self):
        print(self.request_version, " DELETE ", self.path)
        pass

    def do_MKCOL(self):
        print(self.request_version, " MKCOL ", self.path)
        pass

    def do_MOVE(self):
        print(self.request_version, " MOVE ", self.path)
        pass

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
        print(self.request_version, " PUT ", self.path)
        pass

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = WebDAVServer(("", 8080), WebDAVRequestHandler)
    server.serve_forever()
