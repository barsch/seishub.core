from seishub.validator import Validator

class InvalidUriError(Exception):
    pass

class Resource(object):
    """Resource base class"""
    def __init__(self,uri=None,data=None):
        if uri is not None:
            self.setUri(uri)
        else: 
            self.uri=None
        if data is not None:
            self.setData(data)
        else:
            self.data=None
            
    def getData(self):
        return self.data
    
    def setData(self,newdata):
        self.data=newdata
    
    def getUri(self):
        return self.uri
    
    def setUri(self,newuri):
        if self._validateUri(newuri):
            self.uri=newuri
        else:
            raise InvalidUriError
        
    def store(self):
        """should be implemented by subclasses"""
        raise NotImplementedError
    
    def _validateUri(self,value):
        #TODO: do better uri validation here
        if Validator(value).isString() and len(value) > 0:
            return True
        else: 
            return False