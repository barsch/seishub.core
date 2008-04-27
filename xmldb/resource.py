# -*- coding: utf-8 -*-

from seishub.xmldb.validator import Validator
from seishub.xmldb.errors import InvalidUriError
from seishub.xmldb.util import Serializable

class Resource(object):
    """Resource base class"""
    def __init__(self,uri=None,data=None):
        if uri is not None:
            self.setUri(uri)
        else: 
            self.__uri=None
        if data is not None:
            self.setData(data)
        else:
            self.__data=None
            
    def getData(self):
        return self.__data
    
    def setData(self,newdata):
        self.__data = newdata
        return True
    
    data = property(getData, setData, 'Raw data')
    
    def getUri(self):
        return self.__uri
    
    def setUri(self,newuri):
        if self._validateUri(newuri):
            self.__uri=newuri
        else:
            raise InvalidUriError("%s is not a valid URI!" % newuri)
        
    uri = property(getUri, setUri, "Uri")
    
    def _validateUri(self,value):
        #TODO: uri validation
        uri_pattern = ""
        if Validator(value).isString() and len(value) > 0:
            return True
        else: 
            return False
        
class ResourceMetadata(Resource, Serializable):
    """Resource metadata"""
    
    