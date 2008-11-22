# -*- coding: utf-8 -*-

from seishub.exceptions import NotFoundError, ForbiddenError
from seishub.processor.resources.resource import Resource
from twisted.web import static, http, server
import errno
import os


class FileSystemResource(Resource):
    """A file system resource."""
    
    content_types = static.loadMimeTypes()
    content_encodings = {".gz" : "gzip", ".bz2": "bzip2"}
    
    def __init__(self, abspath, default_type="text/html"):
        Resource.__init__(self)
        self.abspath = abspath
        self.is_leaf = True
        if os.path.isfile(abspath):
            self.category = 'file'
            self.folderish = False
        else:
            self.category = 'folder'
            self.folderish = True
        self.default_type = default_type
    
    def render_GET(self, request):
        path = os.path.join(self.abspath, os.sep.join(request.postpath))
        if not os.path.exists(self.abspath):
            raise NotFoundError
        if os.path.isdir(path):
            return self._listDir(path)
        elif os.path.isfile(path):
            return self._getFile(path, request)
        raise NotFoundError
    
    def _getFile(self, path, request):
        ftype, fencoding = static.getTypeAndEncoding(os.path.basename(path),
                                                     self.content_types,
                                                     self.content_encodings,
                                                     self.default_type)
        if ftype:
            request.setHeader('content-type', ftype)
        if fencoding:
            request.setHeader('content-encoding', fencoding)
        
        try:
            fp = open(path, 'rb')
        except IOError, e:
            if e[0] == errno.EACCES:
                raise ForbiddenError
            raise
        
        st = os.stat(path)
        
        # cached
        last_modified = int(float(st.st_mtime))
        if request.setLastModified(last_modified) is http.CACHED:
            return ''
        
        # file size
        fsize = st.st_size
        request.setHeader('content-length', str(fsize))
        if request.method == 'HEAD':
            return ''
        # return data
        static.FileTransfer(fp, fsize, request)
        # and make sure the connection doesn't get closed
        return server.NOT_DONE_YET

    
    def _listDir(self, path):
        """Returns all children."""
        children = {}
        for id in os.listdir(path):
            child_path = os.path.join(path, id)
            children[id] = self._clone(child_path)
        return children
    
    def _clone(self, path):
        return self.__class__(path)
