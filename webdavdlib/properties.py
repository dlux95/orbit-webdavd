from time import time, timezone, strftime, localtime, gmtime
from urllib.parse import quote,unquote

class Property(object):
    name = "undefined"

    def __init__(self, value=None):
        self.value = value

    def get_name(self):
        return self.__class__.name

    def get_value(self):
        return self.value

    def to_xml(self):
        return "<D:%s>%s</D:%s>\n" % (self.get_name(), self.get_value(), self.get_name())


### Basic Properties:
# name
# getcontenttype
# getcontentlength
# creationdate
# iscollection

class NameProperty(Property):
    name = "name"


class ContentTypeProperty(Property):
    name = "getcontenttype"


class ContentLengthProperty(Property):
    name = "getcontentlength"


class CreationDateProperty(Property):
    name = "creationdate"

    def get_value(self):
        return unixdate2iso8601(self.value)


class IsCollectionProperty(Property):
    name = "iscollection"


### Extended Base Properties:
# parentname
# href
# ishidden
# isreadonly
# contentclass
# getcontentlanguage
# lastaccessed
# getlastmodified
# isstructureddocument
# defaultdocument
# displayname
# isroot
# resourcetype

class ParentNameProperty(Property):
    name = "parentname"

class HrefProperty(Property):
    name = "href"

    def get_value(self):
        return quote(self.value)

class IsHiddenProperty(Property):
    name = "ishidden"

class IsReadOnlyProperty(Property):
    name = "isreadonly"

class ContentClassProperty(Property):
    name = "contentclass"

class ContentLanguageProperty(Property):
    name = "getcontentlanguage"

class LastAccessedProperty(Property):
    name = "lastaccessed"

    def get_value(self):
        return unixdate2httpdate(self.value)

class LastModifiedProperty(Property):
    name = "getlastmodified"

    def get_value(self):
        return unixdate2httpdate(self.value)

class IsStructuredDocumentProperty(Property):
    name = "isstructureddocument"

class DefaultDocumentProperty(Property):
    name = "defaultdocument"

class DisplayNameProperty(Property):
    name = "displayname"

class IsRootProperty(Property):
    name = "isroot"

class ResourceTypeProperty(Property):
    name = "resourcetype"

class EtagProperty(Property):
    name = "getetag"

class SupportedLockProperty(Property):
    name = "supportedlock"

    def to_xml(self):
        return "<D:supportedlock>\n" \
               "<D:lockentry>\n" \
               "<D:lockscope><D:exclusive/></D:lockscope>\n" \
               "<D:locktype><D:write/></D:locktype>\n" \
               "</D:lockentry>\n" \
               "<D:lockentry>\n" \
               "<D:lockscope><D:shared/></D:lockscope>\n" \
               "<D:locktype><D:write/></D:locktype>\n" \
               "</D:lockentry>\n" \
               "</D:supportedlock>\n"

class LockDiscoveryProperty(Property):
    name = "lockdiscovery"

    def to_xml(self):
        return "<D:lockdiscovery/>\n"




def unixdate2iso8601(d):
    tz = timezone / 3600 # can it be fractional?
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))
