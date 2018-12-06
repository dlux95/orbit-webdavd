import pathlib
import webdavdlib.exceptions
import webdavdlib
from webdavdlib.properties import *
import random
import hashlib
import os

class Filesystem(object):
    def propfind(self, path, depth):
        raise NotImplementedError()

    def mkcol(self, path):
        raise NotImplementedError()

    def move(self, path, destination):
        raise NotImplementedError()


class HomeFilesystem(Filesystem):
    pass


class DirectoryFilesystem(Filesystem):
    def __init__(self, basepath):
        self.basepath = pathlib.Path(basepath)

        if not self.basepath.is_dir():
            raise webdavdlib.exceptions.NoSuchFileException()

    def create_resource(self, fullpath, basepath):
        if not fullpath.exists():
            return None

        res = webdavdlib.WebDAVResource()
        res.add_property(HrefProperty("/" + str(fullpath.relative_to(basepath).as_posix())))
        res.add_property(LastAccessedProperty(fullpath.stat().st_atime))
        res.add_property(LastModifiedProperty(fullpath.stat().st_mtime))
        res.add_property(CreationDateProperty(fullpath.stat().st_ctime))
        res.add_property(SupportedLockProperty())
        res.add_property(LockDiscoveryProperty())

        if fullpath.is_file():
            res.add_property(ContentLengthProperty(fullpath.stat().st_size))
            res.add_property(ResourceTypeProperty(""))

            etag = hashlib.sha256()
            etag.update(bytes(str(fullpath.stat().st_size), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_mtime), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))

            res.add_property(EtagProperty("\"" + etag.hexdigest() + "\""))

        if fullpath.is_dir():
            res.add_property(ResourceTypeProperty("<D:collection/>"))

            etag = hashlib.sha256()
            etag.update(bytes(str(fullpath.stat().st_mtime), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))

            res.add_property(EtagProperty("\"" + etag.hexdigest() + "\""))


        return res

    def propfind(self, path, depth=0, reslist=None):
        realpath = self.basepath / path

        reslist.append(self.create_resource(realpath, self.basepath))

        if depth > 0:
            if realpath.is_dir():
                for subpath in realpath.iterdir():
                    self.propfind(subpath.relative_to(self.basepath), depth - 1, reslist)

        reslist =  [i for i in reslist if i is not None]
        return reslist

    def mkcol(self, path):
        realpath = self.basepath / path

        try:
            realpath.mkdir(parents=False, exist_ok=False)
        except FileNotFoundError:
            return 409
        except FileExistsError:
            return 409

        return 201

    def move(self, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            os.rename(realpath, realdestination)
        except OSError:
            return 409

        return 201




class MySQLFilesystem(Filesystem):
    pass


class RedisFileSystem(Filesystem):
    pass
