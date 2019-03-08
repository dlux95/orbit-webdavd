
class Authenticator(object):
    def authenticate(self, username, password):
        raise NotImplementedError()

class DebugAuthenticator(Authenticator):
    def authenticate(self, username, password):
        if username == password:
            return True
        else:
            return False

class StaticAuthenticator(Authenticator):
    def __init__(self, mapping):
        self.mapping = mapping

    def authenticate(self, username, password):
        if not username in self.mapping:
            return False

        if not self.mapping[username] == password:
            return False

        return True

class PAMAuthenticator(Authenticator):
    def __init__(self):
        import pam
        self.p = pam.pam()

    def authenticate(self, username, password):
        return self.p.authenticate(username, password, service="system-auth")
