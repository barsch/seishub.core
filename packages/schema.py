# -*- coding: utf-8 -*-
from seishub.util.text import validate_id, to_uri
from seishub.db.util import Serializable

class Schema(Serializable):
    def __init__(self, package_id = None, resourcetype_id = None, 
                 type = None, resource_id = None):
        super(Serializable, self).__init__()
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.type = type
        self.resource_id = resource_id
        
    def __str__(self):
        return to_uri(self.package_id, self.resourcetype_id) + '/' + self.uid
    
    def getResourceTypeId(self):
        return self._resourcetype_id
     
    def setResourceTypeId(self, data):
        self._resourcetype_id = validate_id(data)
        
    resourcetype_id = property(getResourceTypeId, setResourceTypeId, 
                               "Resource type id")
    
    def getPackageId(self):
        return self._package_id
    
    def setPackageId(self, data):
        self._package_id = validate_id(data)
        
    package_id = property(getPackageId, setPackageId, "Package id")
    
    def getResource_id(self):
        return self._resource_id
    
    def setResource_id(self, data):
        self._resource_id = data
        
    resource_id = property(getResource_id, setResource_id, 
                           "Unique resource identifier (integer)")
    
    def getType(self):
        return self._type
    
    def setType(self, data):
        self._type = validate_id(data)
    
    type = property(getType, setType, "Type")
    
    def getResource(self):
        # lazy resource retrieval: to avoid getting all resources in the registry
        # on every query, resources are retrieved only if really needed (and 
        # accessed via schema.resource
        if hasattr(self, '_resource'):
            return self._resource
        if not hasattr(self, '_catalog'):
            return None
        r = self._catalog.xmldb.getResource(resource_id = self.resource_id)
        self._resource = r
        return r

    resource = property(getResource, doc = "XmlResource (read only)")