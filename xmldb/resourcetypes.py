# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.xmldb.interfaces import IResourceTypeRegistry
from seishub.xmldb.util import DbEnabled

class ResourceTypeRegistry(DbEnabled):
    """Resource type registry.
    @see: L{seishub.xmldb.interfaces.IResourceTypeRegistry}"""
    
    implements(IResourceTypeRegistry)
    
    def registerResourceType(self, type, xml_schema):
        """@see: L{seishub.xmldb.interfaces.IResourceTypeRegistry}"""
        
        
    def removeResourceType(self, type):
        """@see: L{seishub.xmldb.interfaces.IResourceTypeRegistry}"""
        
    def getSchema(self, type):
        """@see: L{seishub.xmldb.interfaces.IResourceTypeRegistry}"""
        
    def listResourceTypes(self):
        """@see: L{seishub.xmldb.interfaces.IResourceTypeRegistry}"""
        
    