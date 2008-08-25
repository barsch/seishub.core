from seishub.core import PackageManager
from seishub.packages.interfaces import IGETMapper, IPUTMapper, IPOSTMapper, \
                                        IDELETEMapper

class MapperRegistry(list):
    """
    mappers                     list of urls
    mappers.get(url, method)    get mapper object
    """
    
    methods = {'GET':IGETMapper,
               'PUT':IPUTMapper,
               'POST':IPOSTMapper,
               'DELETE':IDELETEMapper}
    
    def __init__(self, env):
        self.env = env
        
    def _getMapper(self, interface, url):
        all = PackageManager.getClasses(interface)
        mapper = [m for m in all if m.mapping_url == url]
        return mapper
    
    def getMethods(self, url):
        """return list of methods provided by given mapping"""
        methods = list()
        for method, interface in self.methods.iteritems():
            if self._getMapper(interface, url):
                methods.append(method)
        return methods
                
    def get(self, url = None, method = None):
        if not (url and method):
            return self.getMappings()
        interface = self.methods[method.upper()]
        mapper = self._getMapper(interface, url)
        objs = [m(self.env) for m in mapper]
        return objs
    
    def getMappings(self):
        """return list of all known mapping urls"""
        interfaces = self.methods.values()
        all = list()
        for interface in interfaces:
            mapper_classes = PackageManager.getClasses(interface)
            for cls in mapper_classes:
                if cls.mapping_url not in all:
                    all.append(cls.mapping_url)
        all.sort()
        return all