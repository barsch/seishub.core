# -*- coding: utf-8 -*-

from seishub.core import PackageManager, SeisHubError
from seishub.util.text import from_uri
from seishub.db.util import DbStorage
from seishub.packages.interfaces import IPackage, IResourceType, \
                                        IMapperMethod
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper, \
                                     Alias, Schema, Stylesheet
from seishub.packages.util import PackageListProxy, RegistryDictProxy, \
                                  RegistryListProxy, ResourceTypeListProxy


class PackageRegistry(DbStorage):
    """General class to handle all kind of component registration."""
    packages = PackageListProxy()
    resourcetypes = ResourceTypeListProxy()
    aliases = RegistryListProxy('_alias_reg')
    schemas = RegistryListProxy('_schema_reg')
    stylesheets = RegistryListProxy('_stylesheet_reg')
    mappers = RegistryDictProxy('_mapper_reg')
    
    def __init__(self, env):
        DbStorage.__init__(self, env.db)
        self.env = env
        self._stylesheet_reg = StylesheetRegistry(self)
        self._schema_reg = SchemaRegistry(self)
        self._alias_reg = AliasRegistry(self)
        self._mapper_reg = MapperRegistry(self.env)
        
    def getComponents(self, interface, package_id = None):
        """Returns components implementing a certain interface with a given 
        package_id.
        """
        components = PackageManager.getComponents(interface, package_id, 
                                                  self.env)
        return components

    def getPackageIds(self):
        """Returns sorted list of all enabled package ids."""
        all = PackageManager.getPackageIds()
        enabled = [id for id in all if self.env.isComponentEnabled \
                                  (PackageManager.getClasses(IPackage, id)[0])]
        enabled.sort()
        return enabled
    
    def getPackageURLs(self, base=''):
        """Returns sorted list of all enabled package URLs.  Optional a base 
        path can be added in front of each URL.
        """
        return [base + '/' + u for u in self.getPackageIds()]
    
    def isPackageId(self, package_id):
        """Checks if the given package is an enabled package."""
        all = PackageManager.getPackageIds()
        enabled = [id for id in all if self.env.isComponentEnabled \
                                  (PackageManager.getClasses(IPackage, id)[0])]
        return package_id in enabled
    
    def isPackageURL(self, url):
        """Checks if the given URL fits to a package URL."""
        if not url.startswith('/'):
            return False
        return self.isPackageId(url[1:])
    
    def getAllResourceTypes(self):
        """Returns dictionary of enabled resource type ids and package ids, 
        in form of: {'package_id': ['resourcetype_id_1', 'resourcetype_id_2']}.
        """
        package_ids = self.getPackageIds()
        rtypes = dict()
        for p in package_ids:
            all = PackageManager.getClasses(IResourceType, p)
            rtypes[p] = [cls.resourcetype_id for cls in all\
                         if self.env.isComponentEnabled(cls)]
        return rtypes
    
    def getResourceTypes(self, package_id = None):
        """Returns list of all resource types objects, optionally filtered by a
        package id.
        """
        components = self.getComponents(IResourceType, package_id)
        resourcetypes = {}
        for c in components:
            id = c.resourcetype_id
            resourcetypes[id] = c
        return resourcetypes
    
    def getResourceTypeIds(self, package_id):
        """Returns sorted list of all resource type ids filtered by a given 
        package id.
        """
        if not self.isPackageId(package_id):
            return []
        resourcetypes = self.getResourceTypes(package_id).keys()
        resourcetypes.sort()
        return resourcetypes
    
    def getResourceTypeURLs(self, package_id, base=''):
        """Returns a sorted list of resource type URLs filtered by a given
        package id. Optional a base path can be added in front of each URL.
        """
        ids = self.getResourceTypeIds(package_id)
        return [base + '/' + package_id + '/' + id for id in ids]
    
    def isResourceTypeId(self, package_id, resourcetype_id):
        """Checks if a given resource type is an enabled resource type.""" 
        return resourcetype_id in self.getResourceTypeIds(package_id)
    
    def isResourceTypeURL(self, url):
        """Checks if the given URL fits to a resource type URL.""" 
        parts = url.split('/')
        if len(parts)!=3 or parts[0]!='':
            return False
        return self.isResourceTypeId(parts[1], parts[2])
    
    def objects_from_id(self, package_id, resourcetype_id):
        package = None
        resourcetype = None
        if not package_id:
            return package, resourcetype
        package = self.db_getPackage(package_id)
        if not package:
            raise SeisHubError('Package not present in database: %s' %\
                               str(package_id))
        if not resourcetype_id:
            return package, resourcetype
        resourcetype = self.db_getResourceType(package_id, resourcetype_id)
        if not resourcetype:
            raise SeisHubError('Resourcetype not present in database: %s', 
                               str(resourcetype_id))
        return package, resourcetype


    # methods for database registration of packages
    def db_registerPackage(self, package_id, version = ''):
        o = PackageWrapper(package_id, version)
        self.store(o)
        return o
        
    def db_getPackages(self, package_id = None):
        kwargs = dict()
        if package_id:
            kwargs['package_id'] = package_id
        return self.pickup(PackageWrapper, **kwargs)
    
    def db_getPackage(self, package_id):
        try:
            return self.db_getPackages(package_id)[0]
        except IndexError:
            return None
        
    def db_deletePackage(self, package_id):
        #XXX: workaround to check if there are any dependencies on this object
        # as not all dbs are supporting foreign keys
        if not self._is_package_deletable(package_id):
            raise SeisHubError(("Package with id '%s' cannot be deleted due "+\
                               "to other objects depending on it.") %\
                                (str(package_id)))
        self.drop(PackageWrapper, package_id = package_id)
        #except IntegrityError:
        #    raise SeisHubError(("Package with id '%s' cannot be deleted due "+\
        #                       "to other objects depending on it.") %\
        #                        (str(package_id)))
        
    def db_registerResourceType(self, package_id, resourcetype_id,  
                                version = '', version_control = False):
        try:
            package = self.db_getPackages(package_id)[0]
        except IndexError:
            raise SeisHubError('Package not present in database: %s' %\
                               str(package_id))
        o = ResourceTypeWrapper(resourcetype_id, package, 
                                version, version_control)
        self.store(o)
        return o
        
    def db_getResourceTypes(self, package_id = None, resourcetype_id = None):
        kwargs = dict()
        if resourcetype_id:
            kwargs['resourcetype_id'] = resourcetype_id
        if package_id:
            kwargs['package'] = {'package_id':package_id}
        rt = self.pickup(ResourceTypeWrapper, **kwargs)
        return rt
    
    def db_getResourceType(self, package_id, resourcetype_id):
        try:
            return self.db_getResourceTypes(package_id, resourcetype_id)[0]
        except IndexError:
            return None
        
    def db_deleteResourceType(self, package_id, resourcetype_id):
        # XXX: workaround to check if there are any dependencies on this object
        # as not all dbs are supporting foreign keys
        if not self._is_resourcetype_deletable(package_id, resourcetype_id):
            raise SeisHubError(("Resourcetype with id '%s' in package '%s' "+\
                                "cannot be deleted due to other objects " +\
                                "depending on it.") %\
                                (str(resourcetype_id), str(package_id)))
        kwargs = dict()
        package = self.db_getPackages(package_id)[0]
        if not package:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        kwargs['package'] = package
        kwargs['resourcetype_id'] = resourcetype_id
        self.drop(ResourceTypeWrapper, **kwargs)
        
    def _is_package_deletable(self, package_id):
        try:
            p = self.db_getPackages(package_id)[0]
        except IndexError:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        # check if any resourcetype is present:
        resourcetypes = self.db_getResourceTypes(package_id)
        if len(resourcetypes) > 0:
            return False
        # XXX: check if schemas/stylesheets or aliases are present:
        # XXX: check if any catalog entries are present
        return True
    
    def _is_resourcetype_deletable(self, package_id, resourcetype_id):
        try:
            rt = self.db_getResourceTypes(package_id, resourcetype_id)[0] 
        except IndexError:
            raise SeisHubError("Resourcetype with id '%s' in package '%s' "+\
                               "not present in database!", 
                               (str(resourcetype_id), str(package_id)))
        # XXX: check if schemas/stylesheets or aliases are present:
        # XXX: check if any catalog entries are present
        return True
    

class RegistryBase(DbStorage, list):
    """base class for StylesheetRegistry, SchemaRegistry and AliasRegistry
    
    NOTE: a registry object is unambiguously defined by either 
    (package, resourcetype, type) or by (package, type) respectively. """
    
    def __init__(self, registry):
        super(DbStorage, self).__init__(registry.env.db)
        self.catalog = registry.env.catalog
        self.log = registry.env.log
        self.registry = registry
        
    def _split_uri(self, uri):
        resourcetype_id = None
        type = None
        args = uri.split('/')
        package_id = args[1]
        if len(args) == 3: # no resourcetype
            type = args[2]
        else:
            resourcetype_id = args[2]
            type = args[3]
        return package_id, resourcetype_id, type
            
    def register(self, package_id, resourcetype_id, type, xml_data):
        package, resourcetype = self.registry.objects_from_id(package_id, 
                                                              resourcetype_id)
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data)
        try:
            o = self.cls(package, resourcetype, type, res.document._id)
            self.store(o)
        except:
            self.catalog.deleteResource(self.package_id, 
                                        self.resourcetype_id, 
                                        res.document._id)
            raise
        return True
    
    def update(self, package_id, resourcetype_id, type, xml_data):
        pass
    
    def get(self, package_id = None, resourcetype_id = None, type = None, 
            document_id = None, uri = None):
        """Get objects either by (package_id, resourcetype_id, type), 
        by document_id of related XmlDocument or by unique uri"""
        if uri:
            package_id, resourcetype_id, type = self._split_uri(uri)
        keys = {'type':type,
                'resourcetype':None}
        null = []
        if document_id:
            keys['document_id'] = document_id
        if package_id:
            null = ['resourcetype']
            keys['package'] = {'package_id' : package_id}
        if resourcetype_id:
            keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, _null = null, **keys)
        # inject catalog into objs for lazy resource retrieval
        for o in objs:
            o._catalog = self.catalog
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, type = None,
               document_id = None, uri = None):
        o = self.get(package_id, resourcetype_id, type,
                     uri = uri, document_id = document_id)
        if len(o) > 1:
            raise SeisHubError("Unexpected result set length.")
        self.catalog.xmldb.deleteResource(document_id = o[0].document_id)
        self.drop(self.cls, document_id = o[0].document_id)
        return True
    

class SchemaRegistry(RegistryBase):
    _registry = list()
    
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"


class StylesheetRegistry(RegistryBase):
    _registry = list()

    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"


class AliasRegistry(RegistryBase):
    _registry = list()
    cls = Alias
    
    def _split_uri(self, uri):
        args = list(from_uri(uri))
        if args[2].startswith('@'):
            args[2] = args[2][1:]
        return args
    
    def register(self, package_id, resourcetype_id, name, expr, limit = None,
                 order_by = None):
        package, resourcetype = self.registry.objects_from_id(package_id, 
                                                              resourcetype_id)
        o = self.cls(package, resourcetype, name, expr)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
            name = None, expr = None,
            uri = None):
        """Get a single alias by either (package_id, resourcetype_id, name), by 
        expression, or by unique uri.
        Get multiple aliases by (package_id, resourcetype_id) or by package_id.
        """
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        keys = {'name':name,
                'expr':expr}
        null = ['resourcetype']
        if package_id:
            keys['package'] = {'package_id' : package_id}
            keys['resourcetype'] = None
            if resourcetype_id:
                keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, _null = null, **keys)
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, name = None, 
               uri = None):
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        null = list()
        if package:
            null = ['resourcetype_id']
        self.drop(self.cls,
                  package = package,
                  resourcetype = resourcetype,
                  name = name,
                  _null = null)
        return True


class MapperRegistry(dict):
    """
    mappers                     list of urls
    mappers.get(url, method)    get mapper object
    """
    
    methods = dict()
    _registry = dict()
    
    def __init__(self, env):
        self.env = env
        # get available mapper methods
        methods = PackageManager.getClasses(IMapperMethod)
        for m in methods:
            self.methods[m.id] = m.mapper
            self._registry[m.id] = dict()
        self._rebuild()
    
    def _merge_dicts(self, source, target):
        for key in source:
            if key not in target:
                target[key] = source[key]
            else:
                if isinstance(source[key], dict):
                    target[key] = self._merge_dicts(source[key], target[key])
        return target
        
    def _parse_uri(self, uri, cls):
        if len(uri) > 1:
            return {uri[0]:self._parse_uri(uri[1:], cls)}
        else:
            return {uri[0]:{'':cls}}
            
    def _rebuild(self):
        """rebuild the mapper registry"""
        for name, interface in self.methods.iteritems():
            classes = PackageManager.getClasses(interface)
            for cls in classes:
                uri = cls.mapping_url.split('/')[1:]
                uri_dict = self._parse_uri(uri, cls)
                self._registry[name] = self._merge_dicts(uri_dict, 
                                                      self._registry[name])
                
    def _getSupportedMethods(self, cls):
        supported = []
        for method, interface in self.methods.iteritems():
            # XXX: workaround due to seishub's 'implements' not fully beeing 
            # compatible with zope interfaces
            if interface.implementedBy(cls):
                supported.append(method)
            #if interface in cls._implements:
            #    supported.append(method)
        return supported
    
    def _tree_find(self, url, subtree):
        # search direction is top-to-bottom because the url might have an 
        # arbitrary ending
        try:
            return self._tree_find(url[1:], subtree[url[0]])
        except (KeyError, IndexError):
            try:
                return subtree[url[0]]['']
            except KeyError:
                try:
                    return subtree['']
                except KeyError:
                    return None
        
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
        """returns the mapper object on which the given url fits best, 
        deepest path first
        
        if no url and no method is given: get() == getAllMappings()
        
        if only method is given, returns a list of all known mappers for that
        method"""
        if not url and not method:
            return self.getAllMappings()
        if not url:
            return self.getMappings(method)
        url = url.split('/')[1:]
        if not method:
            methods = self.methods.keys()
        else:
            methods = [method]
        objs = list()
        for m in methods:
            mapper_cls = self._tree_find(url, self._registry[m])
            if mapper_cls:
                objs.append(mapper_cls(self.env))
        return list(set(objs))
    
    def getMappings(self, method, base=None):
        """Returns a list of all mappings of a given method with an optional 
        base path.
        """
        # make sure we have a trailing slash for any given base
        if base and not base.endswith('/'):
            base = base + '/'
        mappings = list()
        interface = self.methods[method]
        mapper_classes = PackageManager.getClasses(interface)
        for cls in mapper_classes:
            if not base or cls.mapping_url.startswith(base):
                mappings.append(cls.mapping_url)
        return mappings
    
    def getAllMappings(self):
        """return a dict of all known mappings of the form 
        {uri : [allowed methods]}
        """
        mappings = dict()
        for method, interface in self.methods.iteritems():
            mapper_classes = PackageManager.getClasses(interface)
            for cls in mapper_classes:
                if cls.mapping_url in mappings:
                    mappings[cls.mapping_url].append(method)
                else:
                    mappings[cls.mapping_url] = [method]
        return mappings
