# -*- coding: utf-8 -*-

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
        registry.clear()
        dict.__init__(registry, registry.get())
        return registry
