# -*- coding: utf-8 -*-

from zope.interface import Attribute
from twisted.web import resource


class IResource(resource.IResource):
    """A resource node.
    
    This is an extension of the twisted.web.resource.IResource interface 
    definition. All SeisHub resources should implement this and only this 
    interface!
    """
    
    is_leaf = Attribute("""
        Marker for a leaf node. 
        
        Leaf nodes don't have static children.
        """)
    
    category = Attribute("""
        Defines the category of a node.
        
        Single string representing a category name. Common values are folder, 
        file, mapping, resource, package, resource type or property. The
        requesting service may decide how to handle this information, e.g.
        appending a unique icon for this resource.
        """)
    
    folderish = Attribute("""
        Marker for a folder node. 
        
        Set this to True if you want to inform the requesting service, that 
        this resource behaves like an folder.
        """)


class IFileResource(IResource):
    """A marker interface for a file resource."""
    
    statinfo = Attribute("""
        Result of os.stat system call.
        
        Tuple of ten entries, e.g.:
        (16895, 0L, 0, 0, 0, 0, 16384L, 1227234912, 1227234912, 1180095351).
        
        Please refer to to os.stat documentation for more information.
        """) 


class IXMLResource(IResource):
    """A marker interface for a XML document resource."""


class IMapperResource(IResource):
    """General interface definition for a mapper resource."""
    
    mapping_url = Attribute("""
        Defines the absolute URL of this mapping.
        
        Single string representing a unique mapping URL.
        """)
    
    def process_GET(request):
        """Process a GET request.
        
        This function may return a resource list - a dict in form of 
        {'resource': ['/path/to/resource',], 'mapping': ['/path/to/mapping',]} 
        or a basestring containing a valid XML document. A request at the plain
        mapping_url *must* return a resource list.
        
        If an error occurs it should raise a ProcessorError.
        """
    
    def process_PUT(request):
        """Process a PUT request.
        
        This function should return a string containing the full path to the
        new resource URL, otherwise it should raise a ProcessorError.
        """
    
    def process_POST(request):
        """Process a POST request.
        
        This function should return a string containing the new resource URL if
        the resource could be updated, otherwise it should raise a 
        ProcessorError.
        """
    
    def process_DELETE(request):
        """Process a DELETE request.
        
        This function should return True if the resource could be deleted 
        otherwise it should raise a ProcessorError.
        """
