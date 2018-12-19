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

lockdatabase = []

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
    STDPROP = "" # TODO: Add default allprops

    def get_props(self, path, props=STDPROP):
        """
        Get properties of resouce described by path.

        Returns a list of Property Objects (webdavdlib.properties.*)

        :param path: path to the resource
        :param props: list of properties requested (list of strings)
        :return: list of properties (list of webdavdlib.properties.*)
        """
        raise NotImplementedError()

    def get_children(self, path):
        """
        Get children of a resource described by path. Only suitible for collection resources.

        Returns a list of paths for childs of path

        :param path: path to the resource
        :return: list of child resources
        """
        raise NotImplementedError()

    def get_content(self, path, start=-1, end=-1):
        """
        Get the content of a resource described by path. Only suitible for non-collection resources.
        A start and end byte can be specified to get a specific part of a resource.

        Returns a byte like object of the resource identified by path.

        :param path: path to the resource
        :param start: (optional) start byte (included)
        :param end: (optional) end byte (excluded)
        :return: bytes like object with the content of the resource in the specified range
        """
        raise NotImplementedError()

    def set_content(self, path, content, start=-1):
        """
        Sets the content of a resource described by path. Only suitible for non-collection resources.
        A start byte can be specified to only update a part of a resource.

        Returns True on successful content change. False otherwise.

        :param path: path to the resource
        :param content: byte like content
        :param start: (optional) start byte to update content of the resource
        :return: True or False depending on operation outcome.
        """
        raise NotImplementedError()

    def delete(self, path):
        """
        Deletes the resource described by path. Can be used on collections and non-collections.

        Returns True on successful deletion. False otherwise.
        :param path: path to the resource
        :return: True or False depending on operation outcome.
        """
        raise NotImplementedError()

    def get_uid(self, path):
        """
        Gets a unique identifier for a specific resource. (Should be identical if two filesystems point to
        the same resource). This identifier is used for locking purposes.
        :param path: path to the resource
        :return: unique identifier (string) e.g. path: test/test.txt -> uid: /home/webdav/test/test.txt
        """
        raise NotImplementedError()


class HomeFilesystem(Filesystem):
    pass


class DirectoryFilesystem(Filesystem):
    def __init__(self, basepath):
        self.basepath = pathlib.Path(basepath)

        if not self.basepath.is_dir():
            raise webdavdlib.exceptions.NoSuchFileException()

    def create_resource(self, request, fullpath, basepath):
        if not fullpath.exists():
            return None

        res = webdavdlib.WebDAVResource()
        res.add_property(HrefProperty("/" + str(fullpath.relative_to(basepath).as_posix())))

        res.add_property(LastAccessedProperty(fullpath.stat().st_atime))
        if not "Microsoft Office Excel" in request.headers["User-Agent"]:
            res.add_property(LastModifiedProperty(fullpath.stat().st_mtime))
        res.add_property(CreationDateProperty(fullpath.stat().st_ctime))
        res.add_property(SupportedLockProperty())
        res.add_property(IsHiddenProperty(fullpath.name.startswith(".") or fullpath.name.startswith("~")))
        if fullpath.as_posix() in lockdatabase:
            res.add_property(LockDiscoveryProperty(lockdatabase[fullpath.as_posix()]))
        else:
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
            etag.update(bytes(str(fullpath.stat().st_mtime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_atime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ctime), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_ino), "utf-8"))
            etag.update(bytes(str(fullpath.stat().st_file_attributes), "utf-8"))
            etag.update(bytes("/" + str(fullpath.relative_to(basepath).as_posix()), "utf-8"))
            print("\t", fullpath, " Etag: ", etag.hexdigest())

            res.add_property(EtagProperty("\"" + etag.hexdigest() + "\""))


        return res

    def propfind(self, request, path, depth=0, reslist=None):
        if depth < 0:
            return Status207(None)

        realpath = self.basepath / path

        reslist.append(self.create_resource(request, realpath, self.basepath))

        if depth > 0:
            if realpath.is_dir():
                for subpath in realpath.iterdir():
                    self.propfind(request, subpath.relative_to(self.basepath), depth - 1, reslist)

        reslist =  [i for i in reslist if i is not None]
        return Status207(reslist)

    def mkcol(self, request, path):
        realpath = self.basepath / path

        try:
            realpath.mkdir(parents=False, exist_ok=False)
        except FileNotFoundError:
            return Status409()
        except FileExistsError:
            return Status409()

        return Status201()

    def move(self, request, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            os.rename(realpath, realdestination)
        except OSError:
            return Status409()

        return Status201()

    def move(self, request, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            shutil.copy(realpath, realdestination)
        except OSError:
            return Status409()

        return Status201()

    def get(self, request, path):
        realpath = self.basepath / path

        if not realpath.exists():
            return Status404()

        return Status200(realpath.read_bytes())

    def put(self, request, path, data):
        realpath = self.basepath / path

        try:
            realpath.write_bytes(data)
        except Exception as e:
            print(e)

        return Status200()

    def delete(self, request, path):
        realpath = self.basepath / path

        try:
            if realpath.is_file():
                realpath.unlink()
            else:
                shutil.rmtree(realpath, ignore_errors=True)
        except:
            return Status500()

        return Status204()

    def lock(self, request, path, lockowner):
        realpath = self.basepath / path

        if realpath.as_posix() in lockdatabase:
            locktoken = lockdatabase[realpath.as_posix()][0]
            lockowner = lockdatabase[realpath.as_posix()][1]

            return Status201((locktoken, lockowner, realpath.relative_to(self.basepath).as_posix()))
        else:
            if lockowner == None:
                return Status424()

            locktoken = str(random.getrandbits(128))
            lockdatabase[realpath.as_posix()] = (locktoken, lockowner, realpath.relative_to(self.basepath).as_posix())

            return Status201((locktoken, lockowner, realpath.relative_to(self.basepath).as_posix()))

    def unlock(self, request, path, locktoken):
        realpath = self.basepath / path

        if realpath.as_posix() in lockdatabase:
            if lockdatabase[realpath.as_posix()][0] == locktoken:
                del lockdatabase[realpath.as_posix()]
            else:
                return Status424()
        else:
            return Status424()

        return Status204()




class MySQLFilesystem(Filesystem):
    pass


class RedisFilesystem(Filesystem):
    pass


class MultiplexFilesystem(Filesystem):
    def __init__(self, filesystems):
        self.filesystems = filesystems

    def propfind(self, request, path, depth, reslist=None):
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
                propresults = fs.propfind(request, ".", depth=depth-1, reslist=[]).get_data()
                if propresults == None:
                  continue
                for p in propresults:
                    p.get_property(HrefProperty).set_value("/" + prefix + p.get_property(HrefProperty).get_value())
                res.extend(propresults)


            return Status207([i for i in res if i is not None])

        else:
            vfs = path.parts[0]
            if vfs in self.filesystems:
                res = self.filesystems[vfs].propfind(request, path.relative_to(vfs), depth=depth, reslist=[]).get_data()
                return Status207([i for i in res if i is not None])
            else:
                return Status207()

    def mkcol(self, request, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].mkcol(request, path.relative_to(vfs))
        else:
            return Status409()

    def move(self, request, path, destination):
        vfssource = path.parts[0]
        vfsdestination = path.parts[0]
        if vfssource in self.filesystems and vfsdestination in self.filesystems:
            return self.filesystems[vfssource].move(request, path.relative_to(vfssource), destination.relative_to(vfsdestination))
        else:
            return Status404()

    def get(self, request, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].get(request, path.relative_to(vfs))
        else:
            return Status404()

    def put(self, request, path, data):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].put(request, path.relative_to(vfs), data)
        else:
            return Status500()

    def delete(self, request, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].delete(request, path.relative_to(vfs))
        else:
            return Status500()

    def lock(self, request, path, lockowner):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].lock(request, path.relative_to(vfs), lockowner)
        else:
            return Status500()

    def unlock(self, request, path, locktoken):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].unlock(request, path.relative_to(vfs), locktoken)
        else:
            return Status500()
