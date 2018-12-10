import pathlib
import webdavdlib.exceptions
from webdavdlib.exceptions import *
import webdavdlib
from webdavdlib.properties import *
import random
import hashlib
import os
from webdavdlib.statuscodes import *
import shutil
import shelve

lockdatabase = shelve.open("lock.db")

def getdirsize(path):
    total_size = 0
    start_path = path
    for path, dirs, files in os.walk(start_path):
        for f in files:
            fp = os.path.join(path, f)
            try:
                total_size += os.path.getsize(fp)
            except:
                pass

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

    def delete(self):
        raise NotImplementedError()

    def lock(self, path):
        raise NotImplementedError()

    def unlock(self, path):
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
        res.add_property(IsHiddenProperty(fullpath.name.startswith(".")))

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
            etag.update(bytes(str(fullpath.stat().st_mtime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_atime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ctime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ino), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_file_attributes), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))
            print("\t", fullpath, " Etag: ", etag.hexdigest())

            res.add_property(EtagProperty("\"" + etag.hexdigest() + "\""))


        return res

    def propfind(self, path, depth=0, reslist=None):
        if depth < 0:
            return Status207(None)

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

    def delete(self, path):
        realpath = self.basepath / path

        try:
            if realpath.is_file():
                realpath.unlink()
            else:
                shutil.rmtree(realpath, ignore_errors=True)
        except:
            return Status500()

        return Status204()

    def lock(self, path):
        realpath = self.basepath / path

        locktoken = str(random.getrandbits(128))
        lockdatabase[realpath] = locktoken
        




class MySQLFilesystem(Filesystem):
    pass


class RedisFilesystem(Filesystem):
    pass


class MultiplexFilesystem(Filesystem):
    def __init__(self, filesystems):
        self.filesystems = filesystems

    def propfind(self, path, depth, reslist=None):
        path = pathlib.Path(path)

        if path == pathlib.Path("."):
            # Root path, need to construct virtual folders
            res = []
            root = webdavdlib.WebDAVResource()
            root.add_property(HrefProperty("/."))
            root.add_property(LastAccessedProperty(0))
            root.add_property(LastModifiedProperty(0))
            root.add_property(CreationDateProperty(0))
            root.add_property(SupportedLockProperty())
            root.add_property(LockDiscoveryProperty())
            root.add_property(ResourceTypeProperty("<D:collection/>"))
            root.add_property(EtagProperty("\"" + str(random.getrandbits(128)) + "\""))
            res.append(root)
            for prefix, fs in self.filesystems.items():
                propresults = fs.propfind(".", depth=depth-1, reslist=[]).get_data()
                if propresults == None:
                  continue
                for p in propresults:
                    p.get_property(HrefProperty).set_value("/" + prefix + p.get_property(HrefProperty).get_value())
                res.extend(propresults)


            return Status207([i for i in res if i is not None])

        else:
            vfs = path.parts[0]
            if vfs in self.filesystems:
                res = self.filesystems[vfs].propfind(path.relative_to(vfs), depth=depth, reslist=[]).get_data()
                return Status207([i for i in res if i is not None])
            else:
                return Status207()

    def mkcol(self, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].mkcol(path.relative_to(vfs))
        else:
            return Status409()

    def move(self, path, destination):
        vfssource = path.parts[0]
        vfsdestination = path.parts[0]
        if vfssource in self.filesystems and vfsdestination in self.filesystems:
            return self.filesystems[vfssource].move(path.relative_to(vfssource), destination.relative_to(vfsdestination))
        else:
            return Status404()

    def get(self, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].get(path.relative_to(vfs))
        else:
            return Status404()

    def put(self, path, data):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].put(path.relative_to(vfs), data)
        else:
            return Status500()

    def delete(self, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].delete(path.relative_to(vfs))
        else:
            return Status500()
