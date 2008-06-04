# -*- coding: utf-8 -*-
from seishub.util.text import encode_name
from seishub.db.util import Serializable

class Schema(Serializable):
    def __init__(self, package_id = None, resourcetype_id = None, 
                 type = None, uid = None):
        super(Serializable, self).__init__()
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.type = type
        self.uid = uid
    
    def getFields(self):
        return {'resourcetype_id':self.resourcetype_id,
                'package_id':self.package_id,
                'type':self.type,
                'uid':self.uid
                }
    
    def getResourceTypeId(self):
        return self._resourcetype_id
     
    def setResourceTypeId(self, data):
        self._resourcetype_id = encode_name(data)
        
    resourcetype_id = property(getResourceTypeId, setResourceTypeId, 
                               "Resource type id")
    
    def getPackageId(self):
        return self._package_id
    
    def setPackageId(self, data):
        self._package_id = encode_name(data)
        
    package_id = property(getPackageId, setPackageId, "Package id")
    
    def getUid(self):
        return self._uid
    
    def setUid(self, data):
        self._uid = data
        
    uid = property(getUid, setUid, "Unique resource identifier")
    
    def getType(self):
        return self._type
    
    def setType(self, data):
        self._type = encode_name(data)
    
    type = property(getType, setType, "Type")
    
    def getResource(self):
        # lazy resource retrieval: to avoid getting all resources in the registry
        # on every query, resources are retrieved only if really needed (and 
        # accessed via schema.resource
        if hasattr(self, '_resource'):
            return self._resource
        if not hasattr(self, '_catalog'):
            return None
        r = self._catalog.getResource(self.uid)
        self._resource = r        
        return r

    resource = property(getResource, doc = "XmlResource (read only)")