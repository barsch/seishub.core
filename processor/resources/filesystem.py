# -*- coding: utf-8 -*-

from seishub.exceptions import NotFoundError, ForbiddenError
from seishub.processor.interfaces import IResource, IFileResource
from seishub.processor.resources.resource import Resource
from seishub.util.text import isInteger
from twisted.python import filepath
from twisted.web import static, http, server, script
import errno
from zope.interface import implements


class FileSystemResource(Resource, filepath.FilePath):
    """A file system resource."""
    implements(IFileResource)
    
    content_types = static.loadMimeTypes()
    content_encodings = {".gz" : "gzip", ".bz2": "bzip2"}
    type = None
    
    def __init__(self, path, default_type="text/html", registry=None, 
                 processors = {'.rpy': script.ResourceScript}):
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
    
    def getChild(self, id, request):
        # refresh file stats
        self.restat()
        # are we a directory
        if not self.isdir():
            raise NotFoundError("Item %s is not a valid path" % self.path)
        # ok create new filepath object
        fpath = self.child(id)
        # are we a valid filepath
        if not fpath.exists():
            raise NotFoundError("Item %s does not exists" % id)
        # any processors active ?
        proc = self.processors.get(fpath.splitext()[1].lower())
        if proc:
            return IResource(proc(fpath.path, self.registry))
        return self._clone(fpath.path)
    
    def render_GET(self, request):
        if not self.exists():
            raise NotFoundError("Item %s does not exists." % self.path)
        if self.isdir():
            return self._listDir()
        elif self.isfile():
            return self._getFile(request)
        raise NotFoundError("Don't know how to handle item %s." % self.path)
    
    def _getFile(self, request):
        # check if file
        if not self.exists():
            raise NotFoundError("Item %s is not a file." % self.path)
        # refresh stats
        self.restat()
        # try to open
        try:
            fp = self.open()
        except IOError, e:
            if e[0] == errno.EACCES:
                raise ForbiddenError("Can not access item %s." % self.path)
            raise
        # XXX: cached ? not sure about that yet ...
        last_modified = int(self.getModificationTime())
        if request.setLastModified(last_modified) is http.CACHED:
            return ''
        # content type + encoding
        if not self.type:
            self.type, enc = static.getTypeAndEncoding(self.basename(),
                                                       self.content_types,
                                                       self.content_encodings,
                                                       self.default_type)
        if self.type:
            request.setHeader('content-type', self.type)
        if enc:
            request.setHeader('content-encoding', enc)
        # file size
        fsize = size = self.getsize()
        request.setHeader('content-length', str(fsize))
        if request.method == 'HEAD':
            return ''
        # accept range
        request.setHeader('accept-ranges', 'bytes')
        range = request.getHeader('range')
        # a request for partial data, e.g. Range: bytes=160694272-
        if range and 'bytes=' in range and '-' in range.split('=')[1]:
            parts = range.split('bytes=')[1].strip().split('-')
            if len(parts)==2:
                start = parts[0]
                end = parts[1]
                if isInteger(start):
                    fp.seek(int(start))
                if isInteger(end):
                    end = int(end)
                    size = end
                else:
                    end = size
                request.setResponseCode(http.PARTIAL_CONTENT)
                request.setHeader('content-range',"bytes %s-%s/%s " % (
                     str(start), str(end), str(size)))
                #content-length should be the actual size of the stuff we're
                #sending, not the full size of the on-server entity.
                fsize = end - int(start)
                request.setHeader('content-length', str(fsize))
        
        static.FileTransfer(fp, fsize, request)
        # and make sure the connection doesn't get closed
        return server.NOT_DONE_YET
    
    def _listDir(self):
        """Returns all children."""
        if not self.isdir():
            return {}
        directory = self.listdir()
        directory.sort()
        children = {}
        for id in directory:
            children[id] = self._clone(self.child(id).path)
        return children
    
    def _clone(self, path):
        return self.__class__(path, 
                              default_type=self.default_type, 
                              registry=self.registry,
                              processors = self.processors)
