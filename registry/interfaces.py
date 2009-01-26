# -*- coding: utf-8 -*-

from seishub.packages.interfaces import IPackage, IResourceType


class IPackageWrapper(IPackage):
    """
    Interface definition for a PackageWrapper class.
    
    A PackageWrapper is returned by the registry whenever a Package isn't 
    present in the file system anymore but only in the database.
    """


class IResourceTypeWrapper(IResourceType):
    """
    Interface definition for a ResourceTypeWrapper class.
    
    A ResourceTypeWrapper is returned by the registry whenever a ResourceType 
    isn't present in the file system anymore but only in the database.
    """
