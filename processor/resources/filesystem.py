# -*- coding: utf-8 -*-
"""
File system based resources.
"""

from seishub.exceptions import NotFoundError, ForbiddenError, \
    InternalServerError
from seishub.processor.interfaces import IFileSystemResource, IScriptResource
from seishub.processor.resources.resource import Resource
from twisted.python import filepath
from twisted.web import static, script
from zope.interface import implements


class PythonScript(script.PythonScript):
    implements(IScriptResource)


class ResourceScript(script.ResourceScriptWrapper):
    implements(IScriptResource)


class FileSystemResource(Resource, filepath.FilePath):
    """
    A file system resource.
    """
    implements(IFileSystemResource)
    
    content_types = static.loadMimeTypes()
    content_encodings = {".gz" : "gzip", ".bz2": "bzip2"}
    type = None
    
    def __init__(self, path, default_type="text/html", registry=None, 
                 processors = {'.epy': PythonScript,
                               '.rpy': ResourceScript}):
        Resource.__init__(self)
        filepath.FilePath.__init__(self, path)
        # folder or file?
        self.restat()
        if self.isdir():
            self.category = 'folder'
            self.is_leaf = False
            self.folderish = True 
        else:
            self.category = 'file'
            self.is_leaf = True
            self.folderish = False 
        # content type
        self.default_type = default_type
        # a registry for cached file based scripts
        self.registry = registry or static.Registry()
        # allowed processors
        self.processors = processors
    
    def getMetadata(self):
        self.restat()
        s = self.statinfo
        return {"size"         : s.st_size,
                "uid"          : s.st_uid,
                "gid"          : s.st_gid,
                "permissions"  : s.st_mode,
                "atime"        : s.st_atime,
                "mtime"        : s.st_mtime,
                "nlink"        : s.st_nlink
        }
    
    def getChild(self, id, request):
        # refresh file meta information
        self.restat()
        # are we a directory
        if not self.isdir():
            raise ForbiddenError("Item %s is not a valid path" % self.path)
        # filepath needs to be a Unicode object
        id = id.decode('utf-8')
        # create new FilePath object
        fpath = self.child(id)
        # are we a valid FilePath
        if not fpath.exists():
            raise NotFoundError("Item %s does not exists" % id)
        # any processors active ?
        proc = self.processors.get(fpath.splitext()[1].lower())
        if proc:
            request.setHeader('content-type', 'text/html; charset=UTF-8')
            return proc(fpath.path, self.registry)
        return self._clone(fpath.path)
    
    def _clone(self, path):
        return self.__class__(path, 
                              default_type=self.default_type, 
                              registry=self.registry,
                              processors = self.processors)
    
    def render_GET(self, request):
        """
        Returns either the content of the folder or the file object.
        """ 
        if not self.exists():
            raise NotFoundError("Item %s does not exists." % self.path)
        if self.isdir():
            # return a dictionary of L{FileSystemResource} objects
            ids = sorted(self.listdir())
            children = {}
            for id in ids:
                # IDs retrieved from listdir() are Unicode object 
                safe_id = id.encode('UTF-8')
                children[safe_id] = self._clone(self.child(id).path)
            # add dynamic children
            children.update(self.children)
            return children
        elif self.isfile():
            # return this L{FileSystemResource} object
            return self
        msg = "I don't know how to handle item %s." % self.path
        raise InternalServerError(msg)
