# -*- coding: utf-8 -*-
from seishub.packages.interfaces import IPackage, IResourceType

class RegistryListProxy(object):
    """load a dynamically updated list into a list style registry"""
    def __init__(self, registry):
        self.registry = registry
        
    def __get__(self, obj, objtype):
        registry = obj.__getattribute__(self.registry)
        list.__init__(registry, registry.get())
        return registry
    

class RegistryDictProxy(object):
    """load a dynamically updated dict into a dict style registry"""
    def __init__(self, registry):
        self.registry = registry
        
    def __get__(self, obj, objtype):
        registry = obj.__getattribute__(self.registry)
        dict.__init__(registry, registry.get())
        return registry
    

class PackageListProxy(object):
    """provide registry.packages with an updated list on every access"""
    def __get__(self, obj, objtype):
        return PackageList(obj.getEnabledPackageIds(), obj)
    

class ResourceTypeListProxy(object):
    """provide registry.resourcetypes with an updated list on every access"""
    def __get__(self, obj, objtype):
        return ResourceTypeList(obj.getEnabledResourceTypeIds(), obj)
    

class PackageList(list):
    def __init__(self, values, registry):
        list.__init__(self, values)
        self._registry = registry
        
#    def __getitem__(self, key):
#        return self.get(key)
        
    def get(self, package_id):
        return self._registry.getComponents(IPackage, package_id)[0]


class ResourceTypeList(dict):
    def __init__(self, values, registry):
        dict.__init__(self, values)
        self._registry = registry
        
    def get(self, package_id, resourcetype_id = None):
        if not resourcetype_id:
            return dict.get(self, package_id)
        rtypes = self._registry.getComponents(IResourceType, package_id)
        for rt in rtypes:
            if rt.resourcetype_id == resourcetype_id:
                return rt
        return None