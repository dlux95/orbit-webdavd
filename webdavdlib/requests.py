from urllib.parse import urlparse, unquote
import base64
import re

class BaseRequest(object):
    def __init__(self, httprequest):
        self.path = unquote(httprequest.path)
        self.headers = httprequest.headers
        self.data = ""
        if httprequest.headers.get("Content-Length"):
            self.data = httprequest.rfile.read(int(httprequest.headers.get("Content-Length")))

        self.parseDepth()
        self.parseDestination()
        self.parseAuthorization()
        self.parseLocktoken()
        self.parseOverwrite()

    def parseDestination(self):
        self.destination = None

        if self.headers.get("Destination"):
            self.destination = unquote(self.headers.get("Destination"))

    def parseDepth(self):
        self.depth = None

        if self.headers.get("Depth"):
            raw = self.headers.get("Depth")
            if raw.lower() == "infinity":
                self.depth = 32
            else:
                self.depth = int(raw)


    def parseAuthorization(self):
        self.username = None
        self.password = None

        if self.headers.get("Authorization"):
            stripped = self.headers.get('Authorization')[6:]
            try:
                username, password = base64.b64decode(stripped).decode().split(":")
                self.username = username
                self.password = password
            except:
                pass

    def parseLocktoken(self):
        self.locktoken = None

        if self.headers.get("Lock-Token"):
            try:
                self.locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["Lock-Token"])).group(1)
            except:
                pass

        if self.headers.get("If"):
            try:
                self.locktoken = re.search("<opaquelocktoken:(.*)>", str(self.headers["If"])).group(1)
            except:
                pass

    def parseOverwrite(self):
        self.overwrite = False

        if self.headers.get("Overwrite"):
            self.overwrite = self.headers.get("Overwrite") == "T"


class HeadRequest(BaseRequest):
    pass


class GetRequest(BaseRequest):
    pass


class PutRequest(BaseRequest):
    pass




