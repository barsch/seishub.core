# -*- coding: utf-8 -*-
"""
General processor related interfaces.
"""

from seishub.core import Interface
from zope.interface import Attribute


class IResource(Interface):
    """
    A basic resource node.
    
    All SeisHub resources should implement this and only this interface! Don't
    use twisted resource objects!
    """
    
    is_leaf = Attribute("""
        Marker for a leaf node. 
        
        Leaf nodes don't have usually static children.
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


class IStatical(Interface):
    """
    A marker interface for a static, non blocking resource.
    
    A resource adapting this interface will not be handled inside of a thread.
    So be really sure to use this only for non-blocking code.
    """


class IScriptResource(IResource):
    """
    A marker interface for a file system based script resource.
    """


class IRESTResource(IResource):
    """
    A marker interface for a REST resource.
    """


class IRESTProperty(IResource):
    """
    A marker interface for a REST resource property.
    """


class IFileSystemResource(IResource):
    """
    A marker interface for a file system resource.
    """
    statinfo = Attribute("""
        Result of os.stat system call.
        
        Tuple of ten entries, e.g.:
        (16895, 0L, 0, 0, 0, 0, 16384L, 1227234912, 1227234912, 1180095351).
        
        Please refer to to os.stat documentation for more information.
        """) 
