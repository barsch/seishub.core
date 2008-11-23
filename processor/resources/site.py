# -*- coding: utf-8 -*-

from seishub.processor.resources import Folder
from seishub.util.path import splitPath


class Site(Folder):
    """The root node of the the complete resource tree.
    
    This resource should be instantiated only once. You may add child objects 
    to this folder resource by using an absolute path at the addChild method.
    """
    
    def __init__(self):
        Folder.__init__(self)
        self._registry = {}
    
    def putChild(self, path, obj):
        """Register a static child to the root node.
        
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
                    temp.children[part] = Folder()
                temp = temp.children.get(part)
            temp.children[parts[-1]] = obj
            self._registry[path] = str(obj)
