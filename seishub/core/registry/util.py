# -*- coding: utf-8 -*-

class RegistryListProxy(object):
    """
    Load a dynamically updated list into a list style registry
    """
    def __init__(self, registry):
        self.registry = registry

    def __get__(self, obj, objtype):
        registry = obj.__getattribute__(self.registry)
        list.__init__(registry, registry.get())
        return registry
