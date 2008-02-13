# -*- coding: utf-8 -*-

from seishub.xmldb.validator import Validator
from seishub.xmldb.errors import InvalidUriError

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
        self.__data=newdata
        return True
    
    def getUri(self):
        return self.__uri
    
    def setUri(self,newuri):
        if self._validateUri(newuri):
            self.__uri=newuri
        else:
            raise InvalidUriError
    
    def _validateUri(self,value):
        #TODO: uri validation
        if Validator(value).isString() and len(value) > 0:
            return True
        else: 
            return False