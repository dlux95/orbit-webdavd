from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler, HTTPServer
from webdavdlib import Lock, SystemdHandler, WriteBuffer, get_template, remove_prefix
from webdavdlib.requests import *
from configuration import *

VERSION = "v0.3"

class WebDAVServer(HTTPServer):
    log = logging.getLogger("WebDAVServer")
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        ThreadingHTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.fs = config_filesystems()

        self.authenticator = config_authenticator()

        self.templates = {
            "lock" : get_template("webdavdlib/templates/lock.template.jinja2"),
            "propfind" : get_template("webdavdlib/templates/propfind.template.jinja2"),
            "directory" : get_template("webdavdlib/templates/directory.template.jinja2")
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

        self.log.info("[%s] HEAD Request on %s" % (self.user, request.path))



        filedata = self.server.fs.get_content(self.user, request.path)
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

        self.log.info("[%s] GET Request on %s" % (self.user, request.path))


        try:
            props = self.server.fs.get_props(self.user, request.path, ["D:iscollection"])
            if props["D:iscollection"]:

                children = self.server.fs.get_children(self.user, request.path)

                data = []
                for c in children:
                    cdata = {}
                    cdata["path"] = c
                    cdata["name"] = remove_prefix(c, request.path)
                    cdata["directory"] = self.server.fs.get_props(self.user, c, ["D:iscollection"])["D:iscollection"]
                    cdata["hidden"] = self.server.fs.get_props(self.user, c, ["D:ishidden"])["D:ishidden"]
                    data.append(cdata)

                if request.path != "/":
                    data.append({
                        "path" : os.path.split(request.path)[0],
                        "name" : "..",
                        "hidden" : False,
                        "directory": True
                    })

                sort = sorted(data, key=lambda k: (not k["directory"], k["path"].lower()))

                b = WriteBuffer(self.wfile)
                b.write(self.server.templates["directory"].render(path=request.path, children=sort))
                
                self.log.debug("200 OK")
                self.send_response(200, "OK")
                self.send_header("Content-Length", str(b.getSize()))
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                b.flush()
            else:
                filedata = self.server.fs.get_content(self.user, request.path)
                ctype = props = self.server.fs.get_props(self.user, request.path, ["D:getcontenttype"])["D:getcontenttype"]

                b = WriteBuffer(self.wfile)
                b.write(filedata)

                self.log.debug("200 OK")
                self.send_response(200, "OK")
                self.send_header("Content-Length", str(b.getSize()))
                self.send_header("Content-Type", ctype + "; charset=utf-8")
                self.end_headers()
                b.flush()
        except FileNotFoundError:
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

        self.log.info("[%s] PUT Request on %s with length %d" % (self.user, request.path, len(request.data)))

        exists = True
        try:
            self.server.fs.get_props(self.user, request.path)
        except FileNotFoundError:
            exists = False

        try:
            result = self.server.fs.set_content(self.user, request.path, request.data)

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
        except PermissionError:
            self.log.debug("403 Forbidden")
            self.send_response(403, "Forbidden")
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
        self.log.info("[%s] PROPFIND Request on %s with depth %s and length %d" % (self.user, request.path, depth, len(data)))
        try:
            resqueue = [request.path]
            resdata = {}

            depthqueue = [request.path]
            while depth > 0:
                cpqueue = depthqueue.copy()
                for res in cpqueue:
                    workingres = res
                    for sub in self.server.fs.get_children(self.user, workingres):
                        resqueue.append(sub)
                        depthqueue.append(sub)
                depth = depth-1


            for resource in resqueue:
                workingres = resource.lstrip("/")
                print(workingres)
                resdata[workingres] = self.server.fs.get_props(self.user, resource)
                if request.isexcel:
                    del resdata[workingres]["D:lastmodified"]
                    del resdata[workingres]["D:lastaccessed"]
                    del resdata[workingres]["Z:Win32LastModifiedTime"]
                    del resdata[workingres]["Z:Win32LastAccessTime"]

                resdata[workingres]["lock"] = self.server.get_lock(self.server.fs.get_uid(self.user, resource))

            w = WriteBuffer(self.wfile)
            w.write(self.server.templates["propfind"].render(resdata=resdata))

            self.log.debug("207 Multi-Status")
            self.send_response(207, "Multi-Status")  # Multi-Status
            self.send_header("Content-Type", "text/xml")
            self.send_header("Charset", "utf-8")
            self.send_header("Content-Length", str(w.getSize()))
            self.end_headers()
            w.flush()
            
        except FileNotFoundError:
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

        self.log.info("[%s] DELETE Request on %s" % (self.user, request.path))

        uid = self.server.fs.get_uid(self.user, request.path)
        lock = server.get_lock(uid)

        if lock != None:
            try:
                locktoken = request.locktoken

                if lock.token == locktoken:
                    self.server.fs.delete(self.user, request.path)
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
            self.server.fs.delete(self.user, request.path)

        self.log.debug("204 OK")
        self.send_response(204, "OK")
        self.end_headers()

    def do_MKCOL(self):
        request = MKCOLRequest(self)
        if self.require_auth(request):
            return


        self.log.info("[%s] MKCOL Request on %s with length %d" % (self.user, request.path, len(request.data)))

        try:
            self.server.fs.create(self.user, request.path, dir=True)

            self.log.debug("201 Created")
            self.send_response(201, "Created")
            self.end_headers()
        except PermissionError:
            self.log.debug("403 Forbidden")
            self.send_response(403, "Forbidden")
            self.end_headers()

    def do_PROPPATCH(self):
        #request = PROPPATCHRequest(self)
        #if self.require_auth(request):
            #return

        #self.log.info("[%s] PROPPATCH Request on %s with length %d" % (self.user, request.path, len(request.data)))

        self.do_PROPFIND()


    def copy_element(self, user, source, dest):
        print("Copy element", source, dest)
        if self.server.fs.get_props(self.user, source, ["D:iscollection"])["D:iscollection"]:
            self.server.fs.create(self.user, dest)

            children = self.server.fs.get_children(user, source)
            base = source
            for c in children:
                c_source = "/" + c
                c_destination = dest + c
                self.copy_element(user, c_source, c_destination)
        else:
            try:
                self.server.fs.get_props(self.user, dest, ["D:iscollection"])["D:iscollection"]
            except FileNotFoundError:
                self.server.fs.set_content(self.user, dest, self.server.fs.get_content(self.user, source))



    def do_MOVE(self):
        request = MOVERequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] MOVE Request on %s to %s" % (self.user, request.path, request.destination))

        self.copy_element(self.user, request.path, request.destination)
        self.server.fs.delete(self.user, request.path)

        self.log.debug("204 No-Content")
        self.send_response(204, "No-Content")
        self.send_header('Content-length', '0')
        self.end_headers()

    def do_COPY(self):
        request = COPYRequest(self)
        if self.require_auth(request):
            return

        self.log.info("[%s] COPY Request on %s to %s" % (self.user, request.path, request.destination))

        self.copy_element(self.user, request.path, request.destination)

        self.log.debug("204 No-Content")
        self.send_response(204, "No-Content")
        self.send_header('Content-length', '0')
        self.end_headers()
        

    def do_LOCK(self):
        request = LOCKRequest(self)
        if self.require_auth(request):
            return

        data = request.data
        self.log.info("[%s] LOCK Request on %s with length %d" % (self.user, request.path, len(data)))


        try:
            self.server.fs.get_props(self.user, request.path)
        except FileNotFoundError:
            uid = self.server.fs.get_uid(self.user, request.path)
            lock = Lock(uid, request.lockowner, "exclusive", "infinity", "Second-300")
            self.server.set_lock(uid, lock)
            w = WriteBuffer(self.wfile)
            w.write(self.server.templates["lock"].render(lock=lock))
 
            self.log.debug("200 Ok")
            self.send_response(200, "Ok")
            self.send_header("Lock-Token", "<opaquelocktoken:%s>" % lock.token)
            self.send_header("Content-type", 'text/xml')
            self.send_header("Charset", '"utf-8"')
            self.send_header("Content-Length", str(w.getSize()))
            self.end_headers()

            w.flush()
            return            

        uid = self.server.fs.get_uid(self.user, request.path)
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
        self.log.info("[%s] UNLOCK Request on %s with length %d" % (self.user, request.path, len(data)))

        locktoken = request.locktoken

        uid = self.server.fs.get_uid(self.user, request.path)

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
