# -*- coding: utf-8 -*-

from seishub.registry.package import PackageWrapper, ResourceTypeWrapper, \
    IPackageWrapper, IResourceTypeWrapper


class PackageSpecific(object):
    """Mixin providing package specific information to the class"""
    def __init__(self, *args, **kwargs):
        super(PackageSpecific, self).__init__(*args, **kwargs)
        if len(args) == 2:
            package = args[0]
            resourcetype = args[1]
        elif len(kwargs) == 2:
            package = kwargs.get('package')
            resourcetype = kwargs.get('resourcetype')
        else:
            package = PackageWrapper()
            resourcetype = ResourceTypeWrapper()
        self.package = package
        self.resourcetype = resourcetype
    
    def getPackage(self):
        return self._package
    
    def setPackage(self, data):
        if not IPackageWrapper.providedBy(data):
            raise TypeError('%s is not an IPackageWrapper' % str(data))
        self._package = data
        
    package = property(getPackage, setPackage, "package")
    
    def getResourcetype(self):
        return self._resourcetype
    
    def setResourcetype(self, data):
        if not IResourceTypeWrapper.providedBy(data):
            raise TypeError('%s is not an IResourceTypeWrapper' % str(data))
        self._resourcetype = data
        
    resourcetype = property(getResourcetype, setResourcetype, "resourcetype")