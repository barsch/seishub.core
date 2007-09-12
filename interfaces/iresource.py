from zope.interface import Interface

class IResource(Interface):
    """A basic resource consits at least of an unique uri and optionally
    any kinds of data
    """
    def getUri(self):
        """retrieve the resource's uri """
        
    def setUri(self,newuri):
        """change resource's uri attribute
        a resource cannot be serialized without specifying an uri
        """
        
    def setData(self,newdata):
        """set data attribute"""
        
    def getData(self):
        """retrieve the resource's data"""
        
    def store(self,storage):
        """write resource to a given storage (which implements IStorage)"""
        
    