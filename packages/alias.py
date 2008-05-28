# -*- coding: utf-8 -*-
from seishub.db.util import Serializable

class Alias(Serializable):
    def __init__(self, package_id = None, resourcetype_id = None,
                 name = None, expr = None):
        super(Serializable, self).__init__()
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.name = name
        self.expr = expr
    
    def getFields(self):
        return {'resourcetype_id':self.resourcetype_id,
                'package_id':self.package_id,
                'name':self.name,
                'expr':self.expr
                }
    
    def getResourceTypeId(self):
        return self._resourcetype_id
     
    def setResourceTypeId(self, data):
        self._resourcetype_id = data
        
    resourcetype_id = property(getResourceTypeId, setResourceTypeId, 
                               "Resource type id")
    
    def getPackageId(self):
        return self._package_id
    
    def setPackageId(self, data):
        self._package_id = data
        
    package_id = property(getPackageId, setPackageId, "Package id")
    
    def getName(self):
        return self._name
    
    def setName(self, data):
        if data is not None and not isinstance(data, basestring):
            raise TypeError("Invalid alias name, String expected: %s" % data)
        self._name = data
        
    name = property(getName, setName, "Name of the alias")
    
    def getExpr(self):
        return self._expr
    
    def setExpr(self, data):
        if data is not None and not isinstance(data, basestring):
            raise TypeError("Invalid alias expression, String expected: %s" %\
                             data)
        self._expr = data
        
    expr = property(getExpr, setExpr, "Alias expression (XPath query)")