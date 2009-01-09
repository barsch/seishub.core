# -*- coding: utf-8 -*-

from seishub.core import Interface
from zope.interface import Attribute


class IPackage(Interface):
    """
    This is the main interface for a unique SeisHub package.
    """
    package_id = Attribute("""
        Defines the package ID of this package.
        
        Single string representing a unique package id.
        """)
    
    version = Attribute("""
        Sets the version of this package.
        
        Version may be any string.
    """)


class IPackageWrapper(IPackage):
    """
    Interface definition for a PackageWrapper class.
    
    A PackageWrapper is returned by the registry whenever a Package isn't 
    present in the file system anymore but only in the database.
    """


class IResourceType(IPackage):
    """
    Interface definition for a unique resource type of a package.
    """
    resourcetype_id = Attribute("""Defines the ID of this resource type.""")


class IResourceTypeWrapper(IResourceType):
    """
    Interface definition for a ResourceTypeWrapper class.
    
    A ResourceTypeWrapper is returned by the registry whenever a ResourceType 
    isn't present in the file system anymore but only in the database.
    """


class IMapper(IPackage):
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
    process_POST.optional = 1
    
    def process_DELETE(request):
        """
        Process a DELETE request.
        
        This function should return True if the resource could be deleted 
        otherwise it should raise a ProcessorError.
        """
    
    process_PUT.optional = 1
    process_DELETE.optional = 1


class IAdminPanel(Interface):
    """
    General interface definition for administrative panel.
    """
    template = Attribute("""
        Template file name.
        
        Single string representing the relative path from the module to the 
        template file.
        """)
    
    panel_ids = Attribute("""
        Defines IDs and labels of an admin panel.
        
        Tuple in form of (category, category_label, page, page_label).
        """)
    
    has_roles = Attribute("""
        Defines a list of roles for using this panel.
        
        A list of upper case role names, e.g. SEISHUB_ADMIN or CATALOG_WRITE. 
        Anonymous access will be allowed if this attribute is not defined.
        """)
    
    def render(request):
        """
        Process a request for an admin panel.
        
        This method should return a dictionary of data to be passed to the 
        template defined above.
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
        
        Single string representing the relative path from the 
        L{AdminRootFolder<seishub.processor.resources.admin.AdminRootFolder>}
        to the theme specific CSS file. Implement L{IAdminStaticContent} to 
        introduce new resources to the L{AdminRootFolder}.
        """)


class IAdminStaticContent(Interface):
    """
    Extension point for adding static content to the administration interface.
    """
    
    def getStaticContent():
        """
        Return a dict of static resources (such as css files, images, etc.).
        
        Each entry consists of a 'prefix' and an 'abspath'. The 'prefix' part 
        defines the full path that requests to these resources are prefixed 
        with, e.g. '/images/test.jpg'.
        
        The 'abspath' is the absolute path to the directory containing the
        resources on the local file system.
        """ 


class ISSHCommand(Interface):
    """
    Interface for adding commands to the SSH service.
    """
    
    def getCommandId():
        """
        Return a command string.
        """
    
    def executeCommand(args):
        """
        Process a command line given as an arrays of arguments and 
        returns a list of strings.
        """


class IPostgreSQLView(Interface):
    """
    Interface definition for a PostgreSQL View.
    
    You really have to know what your doing if you are using this interface!
    """
    view_id = Attribute("""
        View ID.
        
        Single string representing the name of this view - this id must match
        the SQL view name, e.g. v_baeume for the following example.
        """)
    
    def createView():
        """
        Return a SQL string creating a view.
        
        e.g. CREATE OR ALTER VIEW v_baeume (name, geom) AS 
             SELECT name, GeomFromText('POINT(' || x || ' ' || y || ')', 4326)
             FROM baeume;
        """
