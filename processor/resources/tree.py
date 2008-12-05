# -*- coding: utf-8 -*-
"""
The root resource of the whole resource tree.
"""

from seishub.processor.resources import RESTFolder, MapperResource, \
    FileSystemResource, AdminRootFolder, StaticFolder
from seishub.util.path import splitPath
import os


class ResourceTree(StaticFolder):
    """
    The root node of the the complete resource tree.
    
    This resource should be instantiated only once. It will auto generate a
    resource tree with standard items like a REST, administrative and mapper
    resources. You may add children to this folder resource by using an 
    absolute path at the putChild method.
    """
    def __init__(self, env):
        StaticFolder.__init__(self)
        self.env = env
        self._registry = {}
        # auto generate tree
        self.update()
    
    def putChild(self, path, obj):
        """
        Register a static child to the root node.
        
        The root node also accepts absolute paths. Missing sub folders are
        automatically generated and added to the resource tree.
        """
        if '/' not in path:
            # we got a single id
            self.children[path] = obj
            self._registry['/' + path] = str(obj) 
        else:
            # we got some absolute path
            parts = splitPath(path)
            temp = self
            for part in parts[:-1]:
                if part not in temp.children:
                    temp.children[part] = StaticFolder()
                temp = temp.children.get(part)
            temp.children[parts[-1]] = obj
            self._registry[path] = str(obj)
    
    def update(self):
        """
        Rebuilds the whole resource tree.
        
        This method should be called, if the status any included resource 
        objects changes, e.g. a mapper gets disabled.
        """
        self.env.log.debug('Updating resource tree.')
        self.children = {}
        self._registry = {}
        # XXX: args favicon - statics from admin panels!
        favicon = os.path.join(self.env.config.path, 'seishub', 'services', 
                               'admin', 'statics', 'favicon.ico' )
        self.putChild('favicon.ico', 
                      FileSystemResource(favicon, "image/x-icon"))
        # set mappings
        for url, cls in self.env.registry.mappers.get().items():
            mapper_obj = cls(self.env)
            self.putChild(url, MapperResource(mapper_obj))
        # set all file system folder
        for url, path in self.env.config.options('fs'):
            self.putChild(url, FileSystemResource(path))
        # set administrative resource
        # XXX: not done yet
        # self.tree.putChild('admin', AdminRootFolder())
        # set XML directory
        self.putChild('xml', RESTFolder())
