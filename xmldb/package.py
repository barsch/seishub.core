from seishub.util.text import validate_id

class PackageSpecific(object):
    """Mixin providing package specific information to the class"""
    def __init__(self, *args, **kwargs):
        super(PackageSpecific, self).__init__(*args, **kwargs)
        if len(args) == 2:
            package_id = args[0]
            resourcetype_id = args[1]
        elif len(kwargs) == 2:
            package_id = kwargs.get('package_id')
            resourcetype_id = kwargs.get('resourcetype_id')
        else:
            package_id = None
            resourcetype_id = None
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
    
    def getPackage_id(self):
        return self._package_id
    
    def setPackage_id(self, data):
        self._package_id = validate_id(data)
        
    package_id = property(getPackage_id, setPackage_id, "package id")
    
    def getResourcetype_id(self):
        return self._resourcetype_id
    
    def setResourcetype_id(self, data):
        self._resourcetype_id = validate_id(data)
        
    resourcetype_id = property(getResourcetype_id, setResourcetype_id, 
                               "resourcetype id")