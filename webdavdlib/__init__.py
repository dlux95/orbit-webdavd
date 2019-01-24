import random
import logging
import sys
import io
from time import strftime, localtime, gmtime, timezone

class Lock(object):
    def __init__(self, uid, owner, mode, depth, timeout):
        self.uid = uid
        self.owner = owner
        self.mode = mode
        self.depth = depth
        self.timeout = timeout
        self.token = str(random.getrandbits(128))


class SystemdHandler(logging.Handler):
    # http://0pointer.de/public/systemd-man/sd-daemon.html
    PREFIX = {
        # EMERG <0>
        # ALERT <1>
        logging.CRITICAL: "<2>",
        logging.ERROR: "<3>",
        logging.WARNING: "<4>",
        # NOTICE <5>
        logging.INFO: "<6>",
        logging.DEBUG: "<7>",
        logging.NOTSET: "<7>"
    }

    def __init__(self, stream=sys.stdout):
        self.stream = stream
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            msg = "%s %s %s\n" % (self.PREFIX[record.levelno], record.name, self.format(record))
            self.stream.write(msg)
            self.stream.flush()
        except Exception:
            self.handleError(record)

class WriteBuffer:
    def __init__(self, w):
        self.w = w
        self.buf = io.BytesIO()

    def write(self, s):

        if isinstance(s, str):
            self.buf.write(s.encode("utf-8"))  # add unicode(s,'utf-8') for chinese code.
        else:
            self.buf.write(s)
    def flush(self):
        self.w.write(self.buf.getvalue())
        self.w.flush()

    def getSize(self):
        return len(self.buf.getvalue())

def unixdate2iso8601(d):
    tz = timezone / 3600 # can it be fractional?
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))
