import pathlib
import webdavdlib.exceptions
import webdavdlib
from webdavdlib.properties import *

class Filesystem(object):
    def get_resource(self, path):
        raise NotImplementedError()


class HomeFilesystem(Filesystem):
    pass


class DirectoryFilesystem(Filesystem):
    def __init__(self, basepath):
        self.basepath = pathlib.Path(basepath)

    def get_resource(self, path, depth=0):
        realpath = (self.basepath / path.lstrip("/")).resolve()
        print("get_resource(", path, ") = ", realpath, " base", self.basepath)
        if not self.basepath in realpath.parents and not self.basepath == realpath:
            raise webdavdlib.exceptions.ForbiddenException

        if realpath.is_dir():
            res = webdavdlib.WebDAVResource()
            res\
                .addProperty(IsCollectionProperty(True))\
                .addProperty(NameProperty(realpath.name))

            return res
        if realpath.is_file():
            res = webdavdlib.WebDAVResource()
            res \
                .addProperty(IsCollectionProperty(False)) \
                .addProperty(NameProperty(realpath.name))\
                .addProperty(ContentLengthProperty(realpath.stat().st_size))\
                .addProperty(LastAccessedProperty(realpath.stat().st_atime))\
                .addProperty(LastModifiedProperty(realpath.stat().st_mtime))\
                .addProperty(CreationDateProperty(realpath.stat().st_ctime))

            return res

        if not realpath.exists():
            return None


class MySQLFilesystem(Filesystem):
    pass


class RedisFileSystem(Filesystem):
    pass
