# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.db.util import Serializable
from seishub.xmldb.interfaces import IResource, IResourceInformation
from seishub.xmldb.package import PackageSpecific

class Resource(object):
    """Resource base class"""
    implements(IResource)
    
    def __init__(self, uid = None, data = None, info = None):
        self.uid = uid
        self.data = data
        self.info = info
            
    def getData(self):
        return self.__data
    
    def setData(self, newdata):
        self.__data = newdata
    
    data = property(getData, setData, 'Raw data')
    
    def getUid(self):
        return self._uid
    
    def setUid(self, data):
        # also set id attribute in ResourceInformation
        if self.info:
            self.info.id = data 
        self._uid = data
    
    uid = property(getUid, setUid, 'unique resource id')
    
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
    
    def __init__(self, res_uid = None, package_id = None, resourcetype_id = None, 
                 revision = None):
        self.id = res_uid
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.revision = revision
        
    def __str__(self):
        return '/'+self.package_id+'/'+self.resourcetype_id+'/'+str(self.id)
    
    #methods and attributes from IResourceInformation
    def getRes_uid(self):
        return self._res_uid
    
    def setRes_uid(self, data):
        self._res_uid = data
    
    id = property(getRes_uid, setRes_uid, "id of resource")
    
    def getRevision(self):
        return self._revision
    
    def setRevision(self, data):
        self._revision = data
         
    revision = property(getRevision,setRevision,"revision")