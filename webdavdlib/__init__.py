import random

class Lock(object):
    def __init__(self, uid, owner, mode, depth, timeout):
        self.uid = uid
        self.owner = owner
        self.mode = mode
        self.depth = depth
        self.timeout = timeout
        self.token = str(random.getrandbits(128))
