class Property(object):
    name = "undefined"
    def __init__(self, value):
        self.value = value

    def getName(self):
        return self.__class__.name

    def getValue(self):
        return self.value


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

class LastModifiedProperty(Property):
    name = "getlastmodified"

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