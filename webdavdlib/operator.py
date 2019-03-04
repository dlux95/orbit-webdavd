from functools import lru_cache
import os

class BaseOperator(object):
    def begin(self, user):
        raise NotImplementedError()

    def end(self, user):
        raise NotImplementedError()


class NoneOperator(object):
    def begin(self, user):
        pass

    def end(self, user):
        pass


class UnixOperator(BaseOperator):
    def __init__(self):
        import pwd
        self.pwd = pwd
        self.counter = 0

    @lru_cache(maxsize=512)
    def get_groups(self, username):
        os.initgroups(username, self.pwd.getpwnam(username)[3])
        g = os.getgroups()
        os.initgroups("root", 0)

        return g

    @lru_cache(maxsize=512)
    def get_pwnam(self, username):
        return self.pwd.getpwnam(username)

    def begin(self, user):
        if self.counter > 1024:
            self.get_groups.cache_clear()
            self.counter = 0

        os.setgroups(self.get_groups(user))
        os.setegid(self.get_pwnam(user)[3])
        os.seteuid(self.get_pwnam(user)[2])

    def end(self, user):
        os.seteuid(0)
        os.setegid(0)
        os.setgroups(self.get_groups("root"))