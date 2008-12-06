# -*- coding: utf-8 -*-
"""
General resource objects.
"""

from seishub.exceptions import NotAllowedError
from seishub.processor.interfaces import IResource, IStaticResource
from zope.interface import implements


class Resource(object):
    """
    A resource object.
    """
    implements(IResource)
    
    def __init__(self):
        self.children = {}
        self.category = 'resource'
        self.folderish = True
        self.is_leaf = False
    
    def getMetadata(self):
        """
        Returns a map of arbitrary metadata. 
        
        As an example, here's what SFTP expects (but doesn't require):
        {
            'size'         : size of file in bytes,
            'uid'          : owner of the file,
            'gid'          : group owner of the file,
            'permissions'  : file permissions,
            'atime'        : last time the file was accessed,
            'mtime'        : last time the file was modified,
            'nlink'        : number of links to the file
        }
        
        Protocols that need metadata should handle the case when a particular 
        value isn't available as gracefully as possible.
        """
        return {'permissions': 0100644}
    
    def putChild(self, id, child):
        """
        Register a static child for this resource.
        """
        self.children[id] = child
    
    def getChild(self, id, request):
        """
        Retrieve a single child resource from me.
        
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
        return self.children.get(id, None)
    
    def getChildWithDefault(self, id, request):
        """
        Retrieve a static or dynamically generated child resource from me.
        
        First checks if a resource was added manually by addChild, and then
        call getChild to check for dynamic resources. Only override if you want
        to affect behaviour of all child lookups, rather than just dynamic
        ones.
        
        This will check to see if I have a pre-registered child resource of the
        given name, and call getChild if I do not.
        """
        if self.children.has_key(id):
            return self.children[id]
        return self.getChild(id, request)
    
    def render(self, request):
        """
        Render a given resource. See L{IResource}'s render method.
        
        I delegate to methods of self with the form 'render_METHOD'
        where METHOD is the HTTP that was used to make the
        request. Examples: render_GET, render_HEAD, render_POST, and
        so on. Generally you should implement those methods instead of
        overriding this one.
        
        render_METHOD methods are expected to return a string which
        will be the rendered page, unless the return value is
        twisted.web.server.NOT_DONE_YET, in which case it is this
        class's responsibility to write the results to
        request.write(data), then call request.finish().
        
        Old code that overrides render() directly is likewise expected
        to return a string or NOT_DONE_YET.
        """
        func = getattr(self, 'render_' + request.method, None)
        if not func:
            allowed_methods = getattr(self, 'allowedMethods', ())
            msg = "This operation is not allowed on this resource."
            raise NotAllowedError(allowed_methods = allowed_methods, 
                                  message = msg)
        return func(request)
    
    def render_HEAD(self, request):
        """
        Default handling of B{HEAD} method.
        
        I just return self.render_GET(request). When method is B{HEAD},
        the framework will handle this correctly.
        """
        return self.render_GET(request)
    
    def render_OPTIONS(self, request):
        """
        Default handling of B{OPTIONS} method.
        """
        request.setHeader("content-length", 0)
        request.setHeader("DAV", "1")
        request.setHeader("Allow", ',' .join(request.allowed_methods))
        return ""


class Folder(Resource):
    """
    A folder resource containing resource objects.
    """
    def __init__(self):
        Resource.__init__(self)
        self.category = 'folder'
    
    def getMetadata(self):
        return {'permissions': 040755}
    
    def render_GET(self, request):
        """
        Returns content of this folder node as dictionary.
        """
        return self.children


class StaticFolder(Folder):
    """
    A static, non-blocking folder resource containing resource objects.
    
    Don't use this folder if you dynamically generate child objects from
    something which could block the whole server, e.g. a database.
    """
    implements(IStaticResource)
