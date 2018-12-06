import pathlib
import webdavdlib.exceptions
import webdavdlib
from webdavdlib.properties import *
import random

class Filesystem(object):
    def get_resources(self, path, depth):
        raise NotImplementedError()


class HomeFilesystem(Filesystem):
    pass


class DirectoryFilesystem(Filesystem):
    def __init__(self, basepath):
        self.basepath = pathlib.Path(basepath)

    def get_resources(self, path, depth=0, reslist=None):
        if reslist == None:
            reslist = []

        try:
            path = path.lstrip("/")
        except:
            pass


        realpath = (self.basepath / path).resolve()
        #print("get_resource(", path, ") = ", realpath, " base", self.basepath)

        if not self.basepath in realpath.parents and not self.basepath == realpath:
            raise webdavdlib.exceptions.ForbiddenException

        if not realpath.exists():
            return None

        if realpath.is_file():
            res = webdavdlib.WebDAVResource()
            res \
                .add_property(HrefProperty("/" + str(pathlib.Path(path).as_posix()))) \
                .add_property(ContentLengthProperty(realpath.stat().st_size)) \
                .add_property(LastAccessedProperty(realpath.stat().st_atime)) \
                .add_property(LastModifiedProperty(realpath.stat().st_mtime)) \
                .add_property(CreationDateProperty(realpath.stat().st_ctime)) \
                .add_property(ResourceTypeProperty("")) \
                .add_property(EtagProperty("\""+str(random.getrandbits(64))+"\""))

            reslist.append(res)

        if realpath.is_dir():
            res = webdavdlib.WebDAVResource()
            res \
                .add_property(HrefProperty("/" + str(pathlib.Path(path).as_posix()))) \
                .add_property(ResourceTypeProperty("<D:collection/>")) \
                .add_property(LastAccessedProperty(realpath.stat().st_atime)) \
                .add_property(LastModifiedProperty(realpath.stat().st_mtime)) \
                .add_property(CreationDateProperty(realpath.stat().st_ctime)) \
                .add_property(EtagProperty("\""+str(random.getrandbits(64))+"\""))

            reslist.append(res)

        if depth > 0:
            if realpath.is_dir():
                for subpath  in realpath.iterdir():
                    self.get_resources((pathlib.Path(path) / subpath.name).as_posix(), depth-1, reslist)

        return reslist




class MySQLFilesystem(Filesystem):
    pass


class RedisFileSystem(Filesystem):
    pass
