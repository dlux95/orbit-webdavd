from webdavdlib.properties import *

class WebDAVResource(object):
    def __init__(self):
        self._properties = []
        self._subresources = []

    def add_property(self, prop):
        if any(p.__class__ == prop.__class__ for p in self._properties):
            print("Duplicate property 1:", prop)
        else:
            self._properties.append(prop)
        return self

    def add_subresource(self, subres):
        self._subresources.append(subres)

    def get_property(self, propclass):
        for p in self._properties:
            if isinstance(p, propclass):
                return p

        return None

    def __str__(self):
        return "WebDAVResource(%s)" % self.get_property(HrefProperty).get_value()
