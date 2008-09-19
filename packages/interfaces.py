# -*- coding: utf-8 -*-

from seishub.core import Interface
from zope.interface import Attribute


class IPackage(Interface):
    """This is the main interface for a unique SeisHub package."""
    
    package_id = Attribute("""
        Defines the package ID of this package.
        
        Single string representing a unique package id.
        """)
    
    version = Attribute("""
        Sets the version of this package.
        
        Version may be any string.
    """)


class IPackageWrapper(IPackage):
    """Interface definition for a PackageWrapper class.
    
    A PackageWrapper is returned by the registry whenever a Package isn't present
    in the file system anymore but only in the database.
    """


class IResourceType(IPackage):
    """Interface definition for a unique resource type of a package."""
    
    resourcetype_id = Attribute("Defines the ID of this resource type.")


class IResourceTypeWrapper(IResourceType):
    """Interface definition for a ResourceTypeWrapper class.
    
    A ResourceTypeWrapper is returned by the registry whenever a ResourceType 
    isn't present in the file system anymore but only in the database.
    """


class IMapperMethod(Interface):
    """General interface definition for a HTTP mapper method."""


class IMapper(Interface):
    """General interface definition for a resource mapper."""
    
    mapping_url = Attribute("""
        Defines the absolute URL of this mapping.
        
        Single string representing a unique mapping URL.
        """)


class IGETMapper(IMapper):
    """Interface definition for a GET resource mapper."""
    
    def processGET(request):
        """Process a GET request.
        
        This function may return a resource list - a dict in form of 
        {'resource': ['/path/to/resource',], 'mapping': ['/path/to/mapping',]} 
        or a basestring containing a valid XML document. A request at the plain
        mapping_url *must* return a resource list.
        
        If an error occurs it should raise a ProcessorError.
        """


class IPUTMapper(IMapper):
    """Interface definition for a PUT resource mapper."""
    
    def processPUT(request):
        """Process a PUT request.
        
        This function should return a string containing the full path to the
        new resource URL, otherwise it should raise a ProcessorError.
        """


class IPOSTMapper(IMapper):
    """Interface definition for a POST resource mapper."""
    
    def processPOST(request):
        """Process a POST request.
        
        This function should return a string containing the new resource URL if
        the resource could be updated, otherwise it should raise a 
        ProcessorError.
        """


class IDELETEMapper(IMapper):
    """Interface definition for a DELETE resource mapper."""
    
    def processDELETE(request):
        """Process a DELETE request.
        
        This function should return True if the resource could be deleted 
        otherwise it should raise a ProcessorError.
        """


class IProperty(Interface):
    """General interface definition for a property file."""


class IPackageProperty(Interface):
    """Interface definition for a package property."""
    
    package_id = Attribute("""
        Defines the package ID of this package property.
        
        Single string representing a unique package id. Leave this attribute
        empty to implement this property for all packages.
        """)


class IResourceTypeProperty(IPackageProperty):
    """Interface definition for a resource type property."""
    
    resourcetype_id = Attribute("""
        Defines the resource type ID of this resource type property.
        
        Single string representing a unique package id. Leave this attribute
        empty to implement this property for all resource types.
        """)
