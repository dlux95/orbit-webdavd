import hashlib, mimetypes, shutil, logging, urllib.parse
from webdavdlib import unixdate2httpdate, path_join, remove_prefix
from webdavdlib.operator import *


STDPROP = ["D:name", "D:getcontenttype", "D:getcontentlength", "D:creationdate", "D:lastaccessed", "D:lastmodified", "D:getlastmodified", "D:resourcetype", "D:iscollection", "D:ishidden", "D:getetag", "D:displayname", "Z:Win32CreationTime", "Z:Win32LastAccessTime", "Z:Win32LastModifiedTime", "Z:Win32FileAttributes"]


class Filesystem(object):
    def get_props(self, user, path, props=STDPROP):
        """
        Get properties of resource described by path.

        Returns a list of property strings.

        :param path: path to the resource
        :param props: list of properties requested (list of strings)
        :return: list of properties (list of strings)
        """
        raise NotImplementedError()

    def get_children(self, user, path):
        """
        Get children of a resource described by path. Only suitible for collection resources.

        Returns a list of paths for childs of path

        :param path: path to the resource
        :return: list of child resources
        """
        raise NotImplementedError()

    def get_content(self, user, path, start=-1, end=-1):
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

    def set_content(self, user, path, content, start=-1):
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

    def create(self, user, path, dir=True):
        """
        Creates a resource that is not existing yet. Primarly used by MKCOL.

        :param path: path to the resource that is being created
        :param dir: should be True when trying to create a directory, creates a file when False
        :return: True or False depending on operation outcome.
        """


    def delete(self, user, path):
        """
        Deletes the resource described by path. Can be used on collections and non-collections.

        Returns True on successful deletion. False otherwise.
        :param path: path to the resource
        :return: True or False depending on operation outcome.
        """
        raise NotImplementedError()

    def get_uid(self, user, path):
        """
        Gets a unique identifier for a specific resource. (Should be identical if two filesystems point to
        the same resource). This identifier is used for locking purposes.
        :param path: path to the resource
        :return: unique identifier (string) e.g. path: test/test.txt -> uid: /home/webdav/test/test.txt
        """
        raise NotImplementedError()


class DirectoryFilesystem(Filesystem):
    log = logging.getLogger("DirectoryFilesystem")

    def __init__(self, basepath, additional_dirs=[], operator=NoneOperator()):
        self.basepath = basepath
        self.additional_dirs = additional_dirs
        self.operator = operator

    def convert_local_to_real(self, path):
        realpath = path_join(self.basepath, path)

        allowed = False
        if realpath.startswith(self.basepath):
            allowed = True
        for add_path in self.additional_dirs:
            if realpath.startswith(add_path):
                allowed = True

        if not allowed:
            self.log.error("Access to ", realpath, " restricted because not under ", self.basepath)
            raise PermissionError()

        return realpath

    def get_content(self, user, path, start=-1, end=-1):
        self.operator.begin(user)
        try:
            path = self.convert_local_to_real(path)
            self.log.debug("get_content(%s)" % path)

            try:
                with open(path, "rb") as f:
                    if start != -1:
                        f.seek(start)

                    if end != -1:
                        return f.read(end-start)
                    else:
                        return f.read()
            except PermissionError:
                raise PermissionError()
        finally:
            self.operator.end(user)

    def set_content(self, user, path, content, start=-1):
        self.operator.begin(user)
        try:
            path = self.convert_local_to_real(path)
            self.log.debug("set_content(%s)" % path)
            mode = "wb"
            if os.path.exists(path):
                mode = "r+b"

            try:
                with open(path, mode) as f:
                    if start != -1:
                        f.seek(start)

                    f.write(content)
            except PermissionError:
                raise PermissionError()
        finally:
            self.operator.end(user)

    def delete(self, user, path):
        self.operator.begin(user)

        try:
            path = self.convert_local_to_real(path)
            self.log.debug("delete(%s)" % path)

            try:
                if os.path.isfile(path):
                    os.unlink(path)
                else:
                    shutil.rmtree(path, ignore_errors=True)
            except PermissionError:
                raise PermissionError
        finally:
            self.operator.end(user)

    def create(self, user, path, dir=True):
        self.operator.begin(user)

        try:
            path = self.convert_local_to_real(path)
            self.log.debug("create(%s)" % path)

            try:
                if dir:
                    os.mkdir(path)
                else:
                    open(path, 'a').close()
            except PermissionError:
                raise PermissionError
        finally:
            self.operator.end(user)

    def get_props(self, user, path, props=STDPROP):
        self.operator.begin(user)

        try:
            rpath = self.convert_local_to_real(path)
            self.log.debug("get_props(%s)" % path)

            if not os.path.exists(rpath):
                raise FileNotFoundError()

            propdata = {"D:status": "200 OK"}

            try:
                for prop in props:
                    propdata[prop] = self._get_prop(rpath, prop, path)
                    self.log.debug("\tProperty %s: %s" % (prop, propdata[prop]))

                return propdata
            except PermissionError:
                raise PermissionError
        finally:
            self.operator.end(user)

    def _get_prop(self, path, prop, urlpath):
        if prop == "D:creationdate" or prop == "Z:Win32CreationTime":
            return unixdate2httpdate(os.path.getctime(path))

        elif prop == "D:lastmodified" or prop == "Z:Win32LastModifiedTime" or prop == "D:getlastmodified":
            return unixdate2httpdate(os.path.getmtime(path))

        elif prop == "D:lastaccessed" or prop == "Z:Win32LastAccessTime":
            return unixdate2httpdate(os.path.getatime(path))

        elif prop == "Z:Win32FileAttributes":
            return "00000000"

        elif prop == "D:ishidden":
            if os.path.split(path)[1].startswith(".") or os.path.split(path)[1].startswith("~"):
                return "1"
            else:
                return False

        elif prop == "D:getcontentlength":
            return os.path.getsize(path)

        elif prop == "D:getcontenttype":
            ty = mimetypes.guess_type(path)[0]
            if ty != None:
                return ty
            else:
                if os.path.isdir(path):
                    return False
                else:
                    return "application/octet-stream"

        elif prop == "D:name" or prop == "D:displayname":
            return urllib.parse.quote(os.path.basename(urlpath.rstrip("/")), safe="/~.$")

        elif prop == "D:resourcetype":
            if os.path.isfile(path):
                return ""
            if os.path.isdir(path):
                return "<D:collection/>"

        elif prop == "D:iscollection":
            if os.path.isdir(path):
                return True
            else:
                return False

        elif prop == "D:getetag":
            etag = hashlib.sha256()
            etag.update(bytes(str(os.path.getsize(path)), "utf-8"))
            etag.update(bytes(str(os.path.getmtime(path)), "utf-8"))
            etag.update(bytes(str(os.path.getctime(path)), "utf-8"))
            etag.update(bytes(str(os.path.getatime(path)), "utf-8"))
            etag.update(bytes(str(os.stat(path).st_ino), "utf-8"))
            etag.update(bytes(path, "utf-8"))
            return "\"%s\"" % etag.hexdigest()


        else:
            return False

    def get_children(self, user, path):
        self.operator.begin(user)

        try:
            rpath = self.convert_local_to_real(path)
            self.log.debug("get_children(%s)" % path)

            try:
                if os.path.isdir(rpath):
                    l = []
                    for sub in os.listdir(rpath):
                        l.append(path_join(path, remove_prefix(sub, self.basepath)))
                    return l
                else:
                    return []
            except PermissionError:
                raise PermissionError()
        finally:
            self.operator.end(user)

    def get_uid(self, user, path):
        self.operator.begin(user)

        try:
            path = self.convert_local_to_real(path)
            self.log.debug("get_uid(%s)" % path)

            return os.path.abspath(path)

        finally:
            self.operator.end(user)


class HomeFilesystem(Filesystem):
    def __init__(self, basepath, additional_dirs=[], operator=None):
        self.basepath = basepath
        self.additional_dirs = additional_dirs
        self.operator = operator

    def get_filesystem(self, user):
         return DirectoryFilesystem(self.operator.get_home(user), self.additional_dirs, self.operator)

    def get_props(self, user, path, props=STDPROP):
        return self.get_filesystem(user).get_props(user, path, props)

    def get_children(self, user, path):
        return self.get_filesystem(user).get_children(user, path)

    def get_content(self, user, path, start=-1, end=-1):
        return self.get_filesystem(user).get_content(user, path, start, end)

    def set_content(self, user, path, content, start=-1):
        return self.get_filesystem(user).set_content(user, path, content, start)

    def create(self, user, path, dir=True):
        return self.get_filesystem(user).create(user, path, dir)

    def delete(self, user, path):
        return self.get_filesystem(user).delete(user, path)

    def get_uid(self, user, path):
        return self.get_filesystem(user).get_uid(user, path)


class MySQLFilesystem(Filesystem):
    pass


class RedisFilesystem(Filesystem):
    pass


class SystemFilesystem(Filesystem):
    pass


class MultiplexFilesystem(Filesystem):
    log = logging.getLogger("MultiplexFilesystem")
    def __init__(self, filesystems):
        self.filesystems = filesystems

    def get_props(self, user, path, props=STDPROP):
        if path == "/":
            # Root path, need to construct virtual folder
            return {"D:status" : "200 OK",
                    "D:name" : "/",
                    "D:creationdate" : unixdate2httpdate(0),
                    "D:lastaccessed" : unixdate2httpdate(0),
                    "D:lastmodified" : unixdate2httpdate(0),
                    "D:getlastmodified": unixdate2httpdate(0),
                    "D:getcontentlength": 4096,
                    "D:resourcetype" : "<D:collection/>",
                    "D:iscollection" : True}
        else:
            vfs = "/" + path.split("/")[1]
            if vfs in self.filesystems:
                return self.filesystems[vfs].get_props(user, "/" + remove_prefix(path, vfs), props)
            else:
                raise FileNotFoundError()

    def get_children(self, user, path):
        if path == "/":
            children = []
            for cpath, fs in self.filesystems.items():
                children.append(cpath)
            return children
        else:
            vfs = "/" + path.split("/")[1]
            if vfs in self.filesystems:
                children = []
                vfschildren = self.filesystems[vfs].get_children(user, "/" + remove_prefix(path, vfs))
                self.log.debug("\tMultiplex children from %s" % (str(vfschildren)))
                for cpath in vfschildren:
                    children.append(path_join(vfs, cpath))
                self.log.debug("\tMultiplex children to %s" % (str(children)))
                return children
            else:
                return []

    def get_content(self, user, path, start=-1, end=-1):
        vfs = "/" + path.split("/")[1]
        if vfs in self.filesystems:
            return self.filesystems[vfs].get_content(user, "/" + remove_prefix(path, vfs), start, end)
        else:
            raise FileNotFoundError()

    def set_content(self, user, path, content, start=-1):
        vfs = "/" + path.split("/")[1]
        if vfs in self.filesystems:
            return self.filesystems[vfs].set_content(user,  "/" + remove_prefix(path, vfs), content, start)
        else:
            raise Exception()

    def create(self, user, path, dir=True):
        vfs = "/" + path.split("/")[1]
        if vfs in self.filesystems:
            return self.filesystems[vfs].create(user,  "/" + remove_prefix(path, vfs), dir)
        else:
            raise Exception()

    def delete(self, user, path):
        vfs = "/" + path.split("/")[1]
        if vfs in self.filesystems:
            return self.filesystems[vfs].delete(user,  "/" + remove_prefix(path, vfs))
        else:
            raise Exception()

    def get_uid(self, user, path):
        if path == "/":
            return "root"
        else:
            vfs = "/" + path.split("/")[1]
            if vfs in self.filesystems:
                return self.filesystems[vfs].get_uid(user,  "/" + remove_prefix(path, vfs))
            else:
                raise Exception()
