# -*- coding: utf-8 -*-

from seishub.exceptions import NotFoundError
from seishub.processor.resources.resource import Resource
import os


class FileSystemResource(Resource):
    """A file system resource."""
    
    def __init__(self, abspath):
        Resource.__init__(self)
        self.abspath = abspath
        self.is_leaf = True
        if os.path.isfile(abspath):
            self.category = 'file'
            self.folderish = False
        else:
            self.category = 'folder'
            self.folderish = True
    
    def process_GET(self, request):
        path = os.path.join(self.abspath, os.sep.join(request.postpath))
        if not os.path.exists(self.abspath):
            raise NotFoundError
        if os.path.isdir(path):
            return self._listDir(path)
        elif os.path.isfile(path):
            fp = open(path, 'r')
            data=fp.read()
            fp.close()
            return data
    
    def _listDir(self, path):
        """Returns all children."""
        children = {}
        for id in os.listdir(path):
            child_path = os.path.join(path, id)
            children[id] = self._clone(child_path)
        return children
    
    def _clone(self, path):
        return self.__class__(path)
