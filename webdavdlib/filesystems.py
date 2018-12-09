import pathlib
import webdavdlib.exceptions
from webdavdlib.exceptions import *
import webdavdlib
from webdavdlib.properties import *
import random
import hashlib
import os
from webdavdlib.statuscodes import *

def getdirsize(path):
    total_size = 0
    start_path = path
    for path, dirs, files in os.walk(start_path):
        for f in files:
            fp = os.path.join(path, f)
            total_size += os.path.getsize(fp)

    return total_size

class Filesystem(object):
    def propfind(self, path, depth):
        raise NotImplementedError()

    def mkcol(self, path):
        raise NotImplementedError()

    def move(self, path, destination):
        raise NotImplementedError()

    def get(self, path):
        raise NotImplementedError()

    def put(self, path, data):
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
            etag.update(bytes(str(fullpath.stat().st_atime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ctime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ino), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_file_attributes), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))
            print("\t", fullpath, " Etag: ", etag.hexdigest())
            res.add_property(EtagProperty("\"" + etag.hexdigest() + "\""))

        if fullpath.is_dir():
            res.add_property(ResourceTypeProperty("<D:collection/>"))

            etag = hashlib.sha256()
            etag.update(bytes(str(getdirsize(fullpath)), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_mtime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_atime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ctime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ino), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_file_attributes), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))
            print("\t", fullpath, " Etag: ", etag.hexdigest(), "Size: ", getdirsize(fullpath))

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
        return Status207(reslist)

    def mkcol(self, path):
        realpath = self.basepath / path

        try:
            realpath.mkdir(parents=False, exist_ok=False)
        except FileNotFoundError:
            return Status409()
        except FileExistsError:
            return Status409()

        return Status201()

    def move(self, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            os.rename(realpath, realdestination)
        except OSError:
            return Status409()

        return Status201()

    def get(self, path):
        realpath = self.basepath / path

        if not realpath.exists():
            return Status404()

        return Status200(realpath.read_bytes())

    def put(self, path, data):
        realpath = self.basepath / path

        try:
            realpath.write_bytes(data)
        except Exception as e:
            print(e)

        return Status200()






class MySQLFilesystem(Filesystem):
    pass


class RedisFileSystem(Filesystem):
    pass
