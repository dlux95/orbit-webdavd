

class WebDAVResource(object):
    def __init__(self):
        self._properties = []
        self._subresources = []

    def addProperty(self, prop):
        if any(p.__class__ == prop.__class__ for p in self._properties):
            print("Duplicate property 1:", prop)
        else:
            self._properties.append(prop)
        return self

    def addSubResource(self, subres):
        self._subresources.append(subres)
