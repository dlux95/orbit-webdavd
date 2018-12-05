
class Authenticator(object):
    def authenticate(self, username, password):
        raise NotImplementedError()

    def require_authentication(self, path):
        raise NotImplementedError()


class DebugAuthenticator(Authenticator):
    def authenticate(self, username, password):
        if username == password:
            return True
        else:
            return False

    def require_authentication(self, path):
        return True
