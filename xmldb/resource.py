# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.db.util import Serializable
from seishub.xmldb.interfaces import IResource, IResourceInformation
from seishub.xmldb.package import PackageSpecific

class Resource(object):
    """Resource base class"""
    implements(IResource)
    
    def __init__(self, resource_id = None, data = None, info = None):
        self.resource_id = resource_id
        self.data = data
        self.info = info
            
    def getData(self):
        return self.__data
    
    def setData(self, newdata):
        self.__data = newdata
    
    data = property(getData, setData, 'Raw data')
    
    def __getId(self):
        return self.__id
    
    def __setId(self, data):
        # also set id attribute in ResourceInformation
        if self.info:
            self.info.resource_id = data 
        self.__id = data
    
    resource_id = property(__getId, __setId, 'unique resource id')
    
    def getInfo(self):
        try:
            return self._info
        except:
            return None
    
    def setInfo(self, data):
        if not IResourceInformation.providedBy(data):
            raise TypeError("%s is not a ResourceInformation" % str(data))
        self._info = data
    
    info = property(getInfo, setInfo, 'resource information')

class ResourceInformation(Serializable, PackageSpecific):
    implements(IResourceInformation)
    
    def __init__(self, package_id = None, resourcetype_id = None, id = None, 
                 revision = None, resource_id = None, version_control = False):
        self.version_control = version_control
        self.id = id
        self.revision = revision
        self.resource_id = resource_id
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        
    def __str__(self):
        return '/'+self.package_id+'/'+self.resourcetype_id+'/'+str(self.id)
    
    # auto update id when _Serializable__id is changed:
    def _setId(self, id):
        Serializable._setId(self, id)
        self.id = id
    
    #methods and attributes from IResourceInformation
    def getRes_id(self):
        return self._resource_id
    
    def setRes_id(self, data):
        self._resource_id = data
    
    resource_id = property(getRes_id, setRes_id, "id of related document "+\
                                                 "(internal id)")
    
    def getRevision(self):
        return self._revision
    
    def setRevision(self, data):
        if not self.version_control:
            self._revision = 1
        else:
            self._revision = data
         
    revision = property(getRevision, setRevision, "revision")
    
    def getId(self):
        return self.__id
    
    def setId(self, data):
        self.__id = data
        
    id = property(getId, setId, "Integer identification number (external id)")