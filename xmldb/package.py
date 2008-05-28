class PackageSpecific(object):
    """Mixin providing package specific information to the class"""
    def __init__(self, *args, **kwargs):
        super(PackageSpecific, self).__init__(*args, **kwargs)
        self.package_id = kwargs.get('package_id')
        self.resourcetype_id = kwargs.get('resourcetype_id')
    
    def getPackage_id(self):
        return self._package_id
    
    def setPackage_id(self, data):
        self._package_id = data
        
    package_id = property(getPackage_id, setPackage_id, "package id")
    
    def getResourcetype_id(self):
        return self._resourcetype_id
    
    def setResourcetype_id(self, data):
        self._resourcetype_id = data
        
    resourcetype_id = property(getResourcetype_id, setResourcetype_id, 
                               "resourcetype id")