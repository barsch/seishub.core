# -*- coding: utf-8 -*-

from seishub.exceptions import NotFoundError, NotImplementedError, ForbiddenError
from seishub.processor.interfaces import IResource
from zope.interface import implements


class Resource:
    """A general resource node."""
    implements(IResource)
    
    def __init__(self):
        self._children = {}
        self.category = 'resource'
        self.folderish = True
        self.is_leaf = False
    
    def addChild(self, id, child):
        """Register a static child."""
        self._children[id] = child
    
    def getChild(self, id, request):
        """Retrieve a single child resource from me.
        
        Implement this to create dynamic resource generation - resources which
        are always available may be registered with self.addChild().
        
        This is meant as an shortcut for checking the availability of a sub
        resource - if you don't implement it, we will lookup a dictionary 
        created by the getChildren method.
        
        This will not be called if the class-level variable 'is_leaf' is set in
        your subclass; instead, the 'postpath' attribute of the request will be
        left as a list of the remaining path elements.
        
        For example, the URL /foo/bar/baz will normally be::
        
          | site.resource.getChild('foo').getChild('bar').getChild('baz').
        
        However, if the resource returned by 'bar' has is_leaf set to True, 
        then the getChild call will never be made on it.
        
        @param id: a string, describing the child
        
        @param request: a twisted.web.server.Request specifying meta-information
                        about the request that is being made for this child.
        """
        return self.getChildren(request).get(id, None)
    
    def getChildren(self, request):
        """Retrieves a list of all dynamically generated child resources.
        
        Implement this for dynamic resource generation. This will not be 
        called if the class-level variable 'is_leaf' is set in your subclass.
        """
        return {}
    
    def getChildWithDefault(self, id, request):
        """Retrieve a static or dynamically generated child resource from me.
        
        First checks if a resource was added manually by addChild, and then
        call getChild to check for dynamic resources. Only override if you want
        to affect behaviour of all child lookups, rather than just dynamic
        ones.
        
        This will check to see if I have a pre-registered child resource of the
        given name, and call getChild if I do not.
        """
        if self._children.has_key(id):
            return self._children[id]
        return self.getChild(id, request)
    
    def getAllChildren(self, request):
        """Retrieve all static or dynamically generated child resources.
        """
        temp = self._children.copy()
        temp.update(self.getChildren(request))
        return temp 
    
    def process(self, request):
        """Process the given request.
        
        I delegate to methods of self with the form 'process_METHOD' where 
        METHOD is the HTTP that was used to make the request, e.g. process_GET,
        process_POST, and so on. Generally you should implement those methods 
        instead of overriding this one.
        """
        func = getattr(self, 'process_' + request.method, None)
        if not func:
            msg = "Method process_%s is not implemented." % (request.method)
            raise NotImplementedError(msg)
        return func(request)


class Folder(Resource):
    """A folder resource containing other objects implementing L{IResource}."""
    
    def __init__(self):
        Resource.__init__(self)
        self.category = 'folder'
    
    def process_GET(self, request):
        """Returns content of this folder node."""
        if len(request.postpath) > 0:
            raise NotFoundError()
        return self.getAllChildren(request)
    
    def process_POST(self, request):
        """Default behaviour for a resource modification request."""
        if len(request.postpath) > 0:
            raise NotFoundError()
        raise ForbiddenError("Operation is not allowed here.")
    
    def process_PUT(self, request):
        """Default behaviour for a resource creation request."""
        raise ForbiddenError("Operation is not allowed here.")
    
    def process_DELETE(self, request):
        """Default behaviour for a resource deletion request."""
        if len(request.postpath) > 0:
            raise NotFoundError()
        raise ForbiddenError("Operation is not allowed here.")
    
    def process_MOVE(self, request):
        """Default behaviour for a resource move request."""
        if len(request.postpath) > 0:
            raise NotFoundError()
        raise ForbiddenError("Operation is not allowed here.")
