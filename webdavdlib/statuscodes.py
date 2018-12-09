

class StatusCode(object):
    code = None
    name = None
    desc = None

    def get_code(self):
        if not self.__class__.code == None:
            return self.__class__.code
        else:
            raise NotImplementedError()

    def get_name(self):
        if not self.__class__.name == None:
            return self.__class__.name
        else:
            raise NotImplementedError()

    def get_description(self):
        if not self.__class__.desc == None:
            return self.__class__.desc
        else:
            raise NotImplementedError()


class Status200(StatusCode):
    code = 200
    name = "OK"
    desc = "Request OK"

class Status201(StatusCode):
    code = 201
    name = "Created"
    desc = "Resource created"

class Status204(StatusCode):
    code = 204
    name = "No Content"
    desc = "Ok without content"

class Status207(StatusCode):
    code = 207
    name = "Multi-Status"
    desc = "Multiple Status Codes"

class Status400(StatusCode):
    code = 400
    name = "Bad Request"
    desc = "Malformatted Request"

class Status403(StatusCode):
    code = 403
    name = "Forbidden"
    desc = "Access to the resource was forbidden"

class Status405(StatusCode):
    code = 405
    name = "Method Not Allowed"
    desc = "Requested Method ist not allowed"

class Status409(StatusCode):
    code = 409
    name = "Conflict"
    desc = "There was a conflict in your request"

class Status412(StatusCode):
    code = 412
    name = "Precondition Failed"
    desc = "Unable to maintain properties or failed overwrite"

class Status415(StatusCode):
    code = 415
    name = "Unsupported Media Type"
    desc = "The server does not support the media type"

class Status423(StatusCode):
    code = 423
    name = "Locked"
    desc = "Resource is locked"

class Status502(StatusCode):
    code = 502
    name = "Bad Gateway"
    desc = "resource on another Server"

class Status507(StatusCode):
    code = 507
    name = "Insufficient Storage"
    desc = "No space left on the device"

