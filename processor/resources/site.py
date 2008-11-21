# -*- coding: utf-8 -*-

from seishub.exceptions import NotFoundError
from seishub.processor.resources import Folder
from seishub.util.path import splitPath


class Site(Folder):
    """The root node of the the whole resource tree.
    
    This resource should be instantiated only once.
    """
    
    def __init__(self):
        Folder.__init__(self)
        self._registry = {}
    
    def addChild(self, path, obj):
        """Register a static child to the root node.
        
        The root node also accepts absolute paths.
        """
        if '/' not in path:
            # we got a single id
            self._children[path] = obj
            
            self._registry['/' + path] = str(obj) 
        else:
            # we got some absolute path
            parts = splitPath(path)
            temp = self
            for part in parts[:-1]:
                if part not in temp._children:
                    temp._children[part] = Folder()
                temp = temp._children.get(part)
            temp._children[parts[-1]] = obj
            self._registry[path] = str(obj)
    
    def start(self, request):
        child = getChildForRequest(self, request)
        return child.process(request)


def getChildForRequest(resource, request):
    """Traverse resource tree to find who will handle the request."""
    
    #print '--->', request.postpath, resource, resource.is_leaf
    while request.postpath and not resource.is_leaf:
        id = request.postpath.pop(0)
        request.prepath.append(id)
        resource = resource.getChildWithDefault(id, request)
        if not resource:
            #print '--->', request.postpath, resource
            raise NotFoundError()
        #print '--->', request.postpath, resource, resource.is_leaf
    return resource
