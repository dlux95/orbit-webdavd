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

        if not self.basepath.is_dir():
            raise webdavdlib.exceptions.NoSuchFileException()

    def create_resource(self, fullpath, basepath):
        if fullpath.is_file():
            res = webdavdlib.WebDAVResource()
            res \
                .add_property(HrefProperty("/" + str(fullpath.relative_to(basepath).as_posix()))) \
                .add_property(ContentLengthProperty(fullpath.stat().st_size)) \
                .add_property(LastAccessedProperty(fullpath.stat().st_atime)) \
                .add_property(LastModifiedProperty(fullpath.stat().st_mtime)) \
                .add_property(CreationDateProperty(fullpath.stat().st_ctime)) \
                .add_property(ResourceTypeProperty("")) \
                .add_property(EtagProperty("\"" + str(random.getrandbits(64)) + "\""))

            return res

        if fullpath.is_dir():
            res = webdavdlib.WebDAVResource()
            res \
                .add_property(HrefProperty("/" + str(fullpath.relative_to(basepath).as_posix()))) \
                .add_property(ResourceTypeProperty("<D:collection/>")) \
                .add_property(LastAccessedProperty(fullpath.stat().st_atime)) \
                .add_property(LastModifiedProperty(fullpath.stat().st_mtime)) \
                .add_property(CreationDateProperty(fullpath.stat().st_ctime)) \
                .add_property(EtagProperty("\""+str(random.getrandbits(64))+"\""))

            return res

        return None

    def get_resources(self, path, depth=0, reslist=None):
        print("get_resources(",path,")")

        realpath = self.basepath / path

        reslist.append(self.create_resource(realpath, self.basepath))

        if depth > 0:
            if realpath.is_dir():
                for subpath in realpath.iterdir():
                    self.get_resources(subpath.relative_to(self.basepath), depth-1, reslist)

        reslist =  [i for i in reslist if i is not None]
        return reslist




class MySQLFilesystem(Filesystem):
    pass


class RedisFileSystem(Filesystem):
    pass
