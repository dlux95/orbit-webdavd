
class Authorizer(object):
    def is_authorized(self, username, path):
        raise NotImplementedError()

class DebugAuthorizer(Authorizer):
    def is_authorized(self, username, path):
        if username == "test":
            return True
