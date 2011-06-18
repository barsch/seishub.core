# -*- coding: utf-8 -*-

from seishub.core.core import Interface, Attribute


class IPackage(Interface):
    """
    This is the main interface for a unique SeisHub package.
    """
    package_id = Attribute("""
        Defines the package ID of this package.
        
        Single string representing a unique package ID.
        """)
    version = Attribute("""
        Sets the version of this package.
        
        Version may be any string.
        """)


class IResourceType(IPackage):
    """
    Interface definition for a unique resource type of a package.
    """
    resourcetype_id = Attribute("""
        Defines the resource type ID of this package.
        
        Single string representing a unique resource type ID.
        """)


class IResourceFormater(Interface):
    """
    Interface definition for a format option of a resource.
    """
    package_id = Attribute("""
        Defines the package ID of this index.
        
        Single string representing the package ID.
        """)
    resourcetype_id = Attribute("""
        Defines the resourcetype ID of this index.
        
        Single string representing the resource type ID.
        """)
    format_id = Attribute("""
        Defines all possible format IDs of the format/output argument.
        
        List of strings representing unique format ID's.
        """)

    def format(request, data, name):
        """
        Formats the resource.
        
        This function should return a formated document and takes care of the
        returned content type.
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
        
        This function may return a resource list - a dictionary in form of 
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
    process_PUT.optional = 1

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
        Defines IDs and labels of an administrative panel.
        
        Tuple in form of (category, category_label, page, page_label).
        """)
    has_roles = Attribute("""
        Defines a list of roles for using this panel.
        
        A list of upper case role names, e.g. SEISHUB_ADMIN or CATALOG_WRITE. 
        Anonymous access will be allowed if this attribute is not defined.
        """)

    def render(request):
        """
        Process a request for an administrative panel.
        
        This method should return a dictionary of data to be passed to the 
        template defined above or a plain string which will be directly rendered
        without using the template.
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

    command_id = Attribute("""
        The SSH command.
        """)

    def executeCommand(request, args):
        """
        Processes a command line.
        
        Request object and a list of arguments are given.
        """


class ISQLView(Interface):
    """
    Interface definition for a SQL View.
    
    You really have to know what your doing if you are using this interface!
    """
    view_id = Attribute("""
        View ID.
        
        Single string representing the name of this view - this id must match
        the SQL view name, e.g. v_baeume for the following example.
        """)

    def createView():
        """
        Return a SQL SELECT statement for creating a SQL view.
        
        e.g. SELECT name, GeomFromText('POINT(' || x || ' ' || y || ')', 4326)
             FROM baeume;
        """


class IProcessorIndex(Interface):
    """
    Interface definition for a custom ProcessorIndex.
    """
    package_id = Attribute("""
        Defines the package ID of this index.
        
        Single string representing the package ID.
        """)
    resourcetype_id = Attribute("""
        Defines the resourcetype ID of this index.
        
        Single string representing the resource type ID.
        """)
    type = Attribute("""
        Data type of the index.
        
        May be any of the types defined in {seishub.xmldb.index}.
        """)
    label = Attribute("""
        Index label.
        
        Single string representing an unique label.
        """)

    def eval(document):
        """
        Evaluate the index on the given resource.
        
        This method has to return a single value or a list of values of the same type as specified 
        in the 'type' attribute.
        
        @param document: document to evaluate the index on
        @type document: {seishub.xmldb.interfaces.IXmlDocument}
        """
