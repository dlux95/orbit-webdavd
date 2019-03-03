from urllib.parse import urlparse
import base64
import re

class BaseRequest(object):
    def __init__(self, path, headers, data):
        self.path = path
        self.headers = headers
        self.data = data

        self.parseDepth()
        self.parseDestination()
        self.parseAuthorization()

    def parseDestination(self):
        self.destination = None

        if self.headers.get("Destination"):
            self.destination = urlparse(self.headers.get("Destination")).path

    def parseDepth(self):
        self.depth = None

        if self.headers.get("Depth"):
            self.depth = self.headers.get("Depth")


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



