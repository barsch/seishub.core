# -*- coding: utf-8 -*-
"""
General processor related interfaces.

XXX: move some of the more general interfaces into the seishub module.
"""

from seishub.core import Interface
from zope.interface import Attribute


class IResource(Interface):
    """
    A resource node.
    
    All SeisHub resources should implement this and only this interface!
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


class IStaticResource(IResource):
    """
    A marker interface for a static, non blocking resource.
    """


class IScriptResource(IResource):
    """
    A marker interface for a filesystem based script resource.
    """


class IRESTResource(IResource):
    """
    A marker interface for a REST resource.
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


class IMapperResource(IResource):
    """
    General interface definition for a mapper resource.
    """
    mapping_url = Attribute("""
        Defines the absolute URL of this mapping.
        
        Single string representing a unique mapping URL.
        """)
    
    def process_GET(request):
        """
        Process a GET request.
        
        This function may return a resource list - a dict in form of 
        {'resource': ['/path/to/resource',], 'mapping': ['/path/to/mapping',]} 
        or a basestring containing a valid XML document. A request at the plain
        mapping_url *must* return a resource list.
        
        If an error occurs it should raise a ProcessorError.
        """
    
    def process_PUT(request):
        """
        Process a PUT request.
        
        This function should return a string containing the full path to the
        new resource URL, otherwise it should raise a ProcessorError.
        """
    
    def process_POST(request):
        """
        Process a POST request.
        
        This function should return a string containing the new resource URL if
        the resource could be updated, otherwise it should raise a 
        ProcessorError.
        """
    
    def process_DELETE(request):
        """
        Process a DELETE request.
        
        This function should return True if the resource could be deleted 
        otherwise it should raise a ProcessorError.
        """


class IAdminPanel(Interface):
    """
    Extension point for adding panels to the administration interface.
    """
    def getPanelId():
        """
        Defines ids and labels of an admin panel.
        
        The items returned by this function must be tuples of the form
        `(category, category_label, page, page_label)`.
        """
    
    def renderPanel(request):
        """
        Process a request for an admin panel.
        
        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template in form of a dictionary.
        """
    
    def getTemplatesDirs():
        """
        Return a list of directories containing template files. Template 
        directories are only bound to one admin panel and can't overwrite 
        system wide templates defined in seishub.services.admin.templates.
        """


class IAdminTheme(Interface):
    """
    A CSS theme for the administrative pages.
    """
    theme_id = Attribute("""
        Theme ID.
        
        Single string representing the name of this theme.
        """)
    
    theme_css_file = Attribute("""
        Path to a CSS file.
        
        Single string representing the relative path to the theme specific
        CSS file.
        """)
    
    def getThemeId():
        """
        Provides a theme specific id and a link to the linked CSS file.
        
        The items returned by this function must be a tuple of the form
        `(theme_id, path_to_css_file)`.
        """