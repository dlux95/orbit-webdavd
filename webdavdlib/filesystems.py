import pathlib
import webdavdlib.exceptions
from webdavdlib.exceptions import *
import webdavdlib
import random
import hashlib
import os
from webdavdlib.statuscodes import *
import shutil
from time import strftime, localtime, gmtime, timezone

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

# TODO: Add default allprops
STDPROP = ["D:name", "D:getcontenttype", "D:getcontentlength", "D:creationdate", "D:lastaccessed", "D:lastmodified", "D:resourcetype", "D:iscollection", "D:ishidden", "D:getetag", "D:displayname"]
class Filesystem(object):


    def get_props(self, path, props=STDPROP):
        """
        Get properties of resource described by path.

        Returns a list of property strings.

        :param path: path to the resource
        :param props: list of properties requested (list of strings)
        :return: list of properties (list of strings)
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

    def create(self, path, dir=True):
        """
        Creates a resource that is not existing yet. Primarly used by MKCOL.

        :param path: path to the resource that is being created
        :param dir: should be True when trying to create a directory, creates a file when False
        :return: True or False depending on operation outcome.
        """


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

    def convert_local_to_real(self, path):
        realpath = self.basepath / path
        if not realpath.as_posix().startswith(self.basepath.as_posix()):
            print("Access to ", realpath, " restricted because not under ", self.basepath)
            raise NoSuchFileException()

        return realpath

    def get_content(self, path, start=-1, end=-1):
        path = self.convert_local_to_real(path)

        with open(path, "r+b") as f:
            if start != -1:
                f.seek(start)

            if end != -1:
                return f.read(end-start)
            else:
                return f.read()

    def set_content(self, path, content, start=-1):
        path = self.convert_local_to_real(path)

        mode = "wb"
        if path.exists():
            mode = "r+b"

        with open(path, mode) as f:
            if start != -1:
                f.seek(start)

            f.write(content)

    def delete(self, path):
        path = self.convert_local_to_real(path)

        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path, ignore_errors=True)

    def create(self, path, dir=True):
        path = self.convert_local_to_real(path)

        if dir:
            path.mkdir(parents=False, exist_ok=False)
        else:
            path.touch(exist_ok=False)

    def get_props(self, path, props=STDPROP):
        path = self.convert_local_to_real(path)

        if not path.exists():
            raise NoSuchFileException()

        propdata = {"D:status": "200 OK"}

        for prop in props:
            propdata[prop] = self._get_prop(path, prop)

        return propdata

    def _get_prop(self, path, prop):
        if prop == "D:creationdate":
            return unixdate2httpdate(path.stat().st_ctime)

        elif prop == "D:lastmodified":
            return unixdate2httpdate(path.stat().st_mtime)

        elif prop == "D:lastaccessed":
            return unixdate2httpdate(path.stat().st_mtime)

        elif prop == "D:ishidden":
            if path.name.startswith(".") or path.name.startswith("~"):
                return "1"
            else:
                return False

        elif prop == "D:getcontentlength":
            return path.stat().st_size

        #elif prop == "D:name" or prop == "D:displayname":
        #    return path.relative_to(self.basepath).name

        elif prop == "D:resourcetype":
            if path.is_file():
                return ""
            if path.is_dir():
                return "<D:collection/>"

        elif prop == "D:iscollection":
            if path.is_dir():
                return True
            else:
                return False

        elif prop == "D:getetag":
            etag = hashlib.sha256()
            etag.update(bytes(str(path.stat().st_size), "utf-8"))
            etag.update(bytes(str(path.stat().st_mtime), "utf-8"))
            etag.update(bytes(str(path.stat().st_atime), "utf-8"))
            etag.update(bytes(str(path.stat().st_ctime), "utf-8"))
            etag.update(bytes(str(path.stat().st_ino), "utf-8"))
            etag.update(bytes(str(path.stat().st_file_attributes), "utf-8"))
            etag.update(bytes(path.as_posix(), "utf-8"))
            return "\"%s\"" % etag.hexdigest()


        else:
            return False

    def get_children(self, path):
        path = self.convert_local_to_real(path)
        if path.is_dir():
            l = []
            for sub in path.iterdir():
                l.append(sub.relative_to(self.basepath).as_posix())
            return l
        else:
            return []


    def move(self, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            os.rename(realpath, realdestination)
        except OSError:
            return Status409()

        return Status201()

    def move(self, path, destination):
        realpath = self.basepath / path
        realdestination = self.basepath / destination

        try:
            shutil.copy(realpath, realdestination)
        except OSError:
            return Status409()

        return Status201()

    def lock(self, path, lockowner):
        realpath = self.basepath / path


        locktoken = str(random.getrandbits(128))

        return Status201((locktoken, lockowner, realpath.relative_to(self.basepath).as_posix()))

    def unlock(self, path, locktoken):
        realpath = self.basepath / path

        return Status204()




class MySQLFilesystem(Filesystem):
    pass


class RedisFilesystem(Filesystem):
    pass


class MultiplexFilesystem(Filesystem):
    def __init__(self, filesystems):
        self.filesystems = filesystems

    def get_props(self, path, props=STDPROP):
        if path == pathlib.Path("."):
            # Root path, need to construct virtual folder
            return {"D:status" : "200 OK",
                    "D:name" : "/",
                    "D:creationdate" : unixdate2httpdate(0),
                    "D:lastaccessed" : unixdate2httpdate(0),
                    "D:lastmodified" : unixdate2httpdate(0),
                    "D:resourcetype" : "<D:collection/>"}
        else:
            vfs = path.parts[0]
            if vfs in self.filesystems:
                return self.filesystems[vfs].get_props(path.relative_to(vfs), props)
            else:
                raise NoSuchFileException()

    def get_children(self, path):
        if path == pathlib.Path("."):
            children = []
            for cpath, fs in self.filesystems.items():
                children.append(pathlib.Path("/" + cpath).relative_to("/").as_posix())
            return children
        else:
            vfs = path.parts[0]
            if vfs in self.filesystems:
                children = []
                for cpath in self.filesystems[vfs].get_children(path.relative_to(vfs)):
                    children.append(pathlib.Path("/" + vfs + "/" + cpath).relative_to("/").as_posix())
                return children
            else:
                return []

    def get_content(self, path, start=-1, end=-1):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].get_content(path.relative_to(vfs), start, end)
        else:
            raise NoSuchFileException()

    def set_content(self, path, content, start=-1):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].set_content(path.relative_to(vfs), content, start)
        else:
            raise Exception()

    def create(self, path, dir=True):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].create(path.relative_to(vfs), dir)
        else:
            raise Exception()

    def delete(self, path):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].delete(path.relative_to(vfs))
        else:
            raise Exception()

    def lock(self, path, lockowner):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].lock(path.relative_to(vfs), lockowner)
        else:
            return Status500()

    def unlock(self, path, locktoken):
        vfs = path.parts[0]
        if vfs in self.filesystems:
            return self.filesystems[vfs].unlock(path.relative_to(vfs), locktoken)
        else:
            return Status500()



def unixdate2iso8601(d):
    tz = timezone / 3600 # can it be fractional?
    tz = '%+03d' % tz
    return strftime('%Y-%m-%dT%H:%M:%S', localtime(d)) + tz + ':00'

def unixdate2httpdate(d):
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(d))