# -*- coding: utf-8 -*-

from seishub.core import PackageManager
from seishub.db.orm import DbStorage, DB_NULL
from seishub.exceptions import SeisHubError, DuplicateObjectError
from seishub.packages.interfaces import IPackage, IResourceType, IMapper, \
    IPostgreSQLView, IProcessorIndex
from seishub.registry.package import Alias, Schema, Stylesheet, PackageWrapper, \
    ResourceTypeWrapper
from seishub.registry.util import RegistryListProxy
from seishub.util.text import from_uri
from seishub.xmldb import index
from sqlalchemy import sql
from zope.interface.verify import verifyClass


class ComponentRegistry(DbStorage):
    """
    General class to handle all kind of component registration.
    """
    aliases = RegistryListProxy('_alias_reg')
    schemas = RegistryListProxy('_schema_reg')
    stylesheets = RegistryListProxy('_stylesheet_reg')
    
    def __init__(self, env):
        DbStorage.__init__(self, env.db)
        self.env = env
        self._stylesheet_reg = StylesheetRegistry(self)
        self._schema_reg = SchemaRegistry(self)
        self._alias_reg = AliasRegistry(self)
        self.mappers = MapperRegistry(self.env)
        self.sqlviews = SQLViewRegistry(self.env)
        self.processor_indexes = ProcessorIndexRegistry(self.env)
    
    def getComponents(self, interface, package_id = None):
        """
        Returns components implementing a certain interface with a given 
        package_id.
        """
        components = PackageManager.getComponents(interface, package_id, 
                                                  self.env)
        return components
    
    def getPackage(self, package_id):
        """
        Returns a single package object.
        """
        pkg = self.getComponents(IPackage, package_id)
        if not pkg:
            raise SeisHubError(("Package with id '%s' not found. Make sure " +\
                               "the package has been enabled.") % (package_id))
        return pkg[0] 
        

    def getPackageIds(self):
        """
        Returns sorted list of all enabled package ids.
        """
        all = PackageManager.getPackageIds()
        enabled = [id for id in all if self.env.isComponentEnabled \
                   (PackageManager.getClasses(IPackage, id)[0])]
        return sorted(enabled)
    
    def isPackageId(self, package_id):
        """
        Checks if the given package id belongs to an enabled package.
        """
        return package_id in self.getPackageIds()
    
    def getAllPackagesAndResourceTypes(self):
        """
        Returns dictionary of enabled resource type ids and package ids, 
        in form of: {'package_id': ['resourcetype_id_1', 'resourcetype_id_2']}.
        """
        ids = self.getPackageIds()
        resourcetypes = dict()
        for id in ids:
            all = PackageManager.getClasses(IResourceType, id)
            resourcetypes[id] = [cls.resourcetype_id for cls in all \
                                if self.env.isComponentEnabled(cls)]
        return resourcetypes
    
    def getResourceType(self, package_id, resourcetype_id):
        """
        Returns a single resource type object.
        """
        components = self.getComponents(IResourceType, package_id)
        for obj in components:
            if obj.resourcetype_id == resourcetype_id:
                return obj
        return None
    
    def getResourceTypes(self, package_id):
        """
        Returns a list of all enabled resource types for a given package id.
        """
        all = PackageManager.getClasses(IResourceType, package_id)
        return [cls for cls in all if self.env.isComponentEnabled(cls)]
    
    def getResourceTypeIds(self, package_id):
        """
        Returns a sorted list of all enabled resource type ids for a given 
        package id.
        """
        if not self.isPackageId(package_id):
            return []
        all = self.getResourceTypes(package_id)
        enabled = [cls.resourcetype_id for cls in all]
        return sorted(enabled)
    
    def isResourceTypeId(self, package_id, resourcetype_id):
        """
        Checks if a given resource type is an enabled resource type.
        """ 
        return resourcetype_id in self.getResourceTypeIds(package_id)
    
    # XXX: refactor the rest into different module
    
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
            raise SeisHubError('Resourcetype not present in database: %s' % 
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
            self.db_getPackages(package_id)[0]
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
            self.db_getResourceTypes(package_id, resourcetype_id)[0] 
        except IndexError:
            msg = "Resourcetype '%s' in package '%s' not present in database!"
            raise SeisHubError(msg % (str(resourcetype_id), str(package_id)))
        # XXX: check if schemas/stylesheets or aliases are present:
        # XXX: check if any catalog entries are present
        return True


class RegistryBase(DbStorage, list):
    """
    Base class for StylesheetRegistry, SchemaRegistry and AliasRegistry.
    
    NOTE: a registry object is unambiguously defined by either 
    (package, resourcetype, type) or by (package, type) respectively.
    """
    
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
        elif len(args) == 4:
            resourcetype_id = args[2]
            type = args[3]
        else:
            raise SeisHubError("Invalid URL: %s" % uri)
        return package_id, resourcetype_id, type
    
    def register(self, package_id, resourcetype_id, type, xml_data, name=None):
        package, resourcetype = self.registry.objects_from_id(package_id, 
                                                              resourcetype_id)
        if name:
            name = '_'.join([package_id, resourcetype_id or '', name])
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data, name=name)
        try:
            o = self.cls(package, resourcetype, type, res.document._id)
            self.store(o)
        except:
            self.catalog.deleteResource(res)
            raise
        return True
    
    def update(self, package_id, resourcetype_id, type, xml_data):
        pass
    
    def get(self, package_id = None, resourcetype_id = None, type = None, 
            document_id = None, uri = None):
        if uri:
            package_id, resourcetype_id, type = self._split_uri(uri)
        keys = {'package':None,
                'resourcetype':None,
                'type':type
                }
        if document_id:
            keys['document_id'] = document_id
        if package_id:
            keys['package'] = {'package_id' : package_id}
        if resourcetype_id == DB_NULL:
            keys['resourcetype'] = DB_NULL
        elif resourcetype_id:
            keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, **keys)
        # inject catalog into objs for lazy resource retrieval
        for o in objs:
            o._catalog = self.catalog
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, type = None,
               document_id = None, uri = None):
        o = self.get(package_id, resourcetype_id, type,
                     uri = uri, document_id = document_id)
        if len(o) > 1:
            raise SeisHubError("Error deleting a schema or stylesheet: " +\
                               "Unexpected result set length.")
        if len(o) == 0:
            raise SeisHubError("Error deleting a schema or stylesheet: " +\
                               "No objects found with the given parameters.")
        self.catalog.deleteResource(resource_id = o[0]._id)
        self.drop(self.cls, document_id = o[0].document_id)
        return True


class SchemaRegistry(RegistryBase):
    _registry = list()
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"
    
    def _split_uri(self, uri):
        resourcetype_id = None
        type = None
        args = uri.split('/')
        package_id = args[1]
        if len(args) == 3: # no type
            resourcetype_id = args[2]
        elif len(args) == 4:
            resourcetype_id = args[2]
            type = args[3]
        else:
            raise SeisHubError("Invalid URL: %s" % uri)
        return package_id, resourcetype_id, type
    
    def register(self, package_id, resourcetype_id, type, xml_data, name=None):
        """
        Register a schema.
        
        @param package_id: package id
        @type package_id: str
        @param resourcetype_id: resourcetype id
        @type resourcetype_id: str
        @param type: type / additional label
        @type type: str
        @param xml_data: Xml data of schema.
        @type xml_data: str
        @param name: optional resource name
        @type name: str
        """
        if not resourcetype_id:
            raise SeisHubError("Schemas must have a resourcetype.")
        return RegistryBase.register(self, package_id, resourcetype_id, type, 
                                     xml_data, name)
    
    def get(self, package_id = None, resourcetype_id = None, type = None, 
            document_id = None, uri = None):
        """
        Get schemas either by (package_id, resourcetype_id, type), 
        by document_id of related XmlDocument or by uri.
        
        The following parameter combinations return a single schema:
         - get(package_id, resourcetype_id, type)
         - get(document_id = ...)
        
        The following combinations return multiple schemas:
         - get(package_id, resourcetype_id)
         - get(package_id)
         - get() -> all stylesheets
        """
        return RegistryBase.get(self, package_id, resourcetype_id, type, 
                                document_id, uri)
    
    def delete(self, package_id = None, resourcetype_id = None, type = None,
               document_id = None, uri = None):
        """
        Remove a schema from the registry.
        
        Deletion of multiple schemas is not allowed. Therefore the following 
        parameter combinations are allowed:
         - delete(package_id, resourcetype_id, type)
         - delete(document_id = ...)
         - delete(uri = ...)
        """
        return RegistryBase.delete(self, package_id, resourcetype_id, type, 
                                   document_id, uri)


class StylesheetRegistry(RegistryBase):
    _registry = list()
    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"
    
    def register(self, package_id, resourcetype_id, type, xml_data, name=None):
        """
        Register a stylesheet.
        
        @param package_id: package id
        @type package_id: str
        @param resourcetype_id: resourcetype id (may be None)
        @type resourcetype_id: str | NoneType
        @param type: type / additional label
        @type type: str
        @param xml_data: Xml data of schema.
        @type xml_data: str
        @param name: optional resource name
        @type name: str
        """
        return RegistryBase.register(self, package_id, resourcetype_id, type, 
                                     xml_data, name)
    
    def get(self, package_id = None, resourcetype_id = None, type = None, 
            document_id = None, uri = None):
        """
        Get stylesheets either by (package_id, resourcetype_id, type), 
        by document_id of related XmlDocument or by uri.
        
        The following parameter combinations return a single stylesheet:
         - get(package_id, resourcetype_id, type) -> resourcetype specific
         - get(package_id, None, type) -> package specific
         - get(document_id = ...)
         
        The following combinations return multiple stylesheets:
         - get(package_id, resourcetype_id) -> resourcetype specific
         - get(package_id) -> package specific
         - get() -> all stylesheets
        """
        if package_id:
            resourcetype_id = resourcetype_id or DB_NULL
        return RegistryBase.get(self, package_id, resourcetype_id, type, 
                                document_id, uri)
    
    def delete(self, package_id = None, resourcetype_id = None, type = None,
               document_id = None, uri = None):
        """
        Remove a stylesheet from the registry.
        
        Deletion of multiple stylesheets is not allowed. Therefore the 
        following parameter combinations are allowed:
         - delete(package_id, resourcetype_id, type)
         - delete(package_id, None, type)
         - delete(document_id = ...)
         - delete(uri = ...)
        """
        return RegistryBase.delete(self, package_id, resourcetype_id, type, 
                                   document_id, uri)


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
            name = None, expr = None, limit = None, order_by = None,
            uri = None):
        """
        Get a single alias by either (package_id, resourcetype_id, name), by 
        expression, or by unique uri.
        Get multiple aliases by (package_id, resourcetype_id) or by package_id.
        """
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        keys = {'name':name,
                'expr':expr}
        if package_id:
            keys['package'] = {'package_id' : package_id}
            keys['resourcetype'] = DB_NULL
            if resourcetype_id:
                keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, **keys)
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, name = None, 
               uri = None):
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        null = list()
        if package:
            null = ['resourcetype_id']
        if name:
            name = str(name)
        self.drop(self.cls,
                  package = package,
                  resourcetype = resourcetype,
                  name = name,
                  _null = null)
        return True


class MapperRegistry(dict):
    """
    The Mapper registry.
    
    This dictionary contains all activated mappings.
    """
    _urls = dict()
    
    def __init__(self, env):
        self.env = env
    
    def update(self):
        """
        Refresh the mapper registry.
        """
        self._urls = dict()
        all = PackageManager.getClasses(IMapper)
        for cls in all:
            if not self.env.isComponentEnabled(cls):
                continue
            # sanity checks
            if not hasattr(cls, 'mapping_url'):
                msg = "Class %s has a wrong implementation of %s. " + \
                      "Attribute mapping_url is missing."
                self.env.log.warn(msg % (cls, IMapper))
                continue
            self._urls[cls.mapping_url] = cls
    
    def get(self, url = None):
        """
        Returns a dictionary of a mapper objects {'/path/to': mapper_object}.
        """
        if not url:
            return self._urls
        else:
            return self._urls.get(url, None)


class SQLViewRegistry(object):
    """
    The SQL View registry.
    """
    _view_objs = dict()
    
    def __init__(self, env):
        self.env = env
    
    def update(self):
        """
        Refresh all SQL views.
        """
        self._view_objs = dict()
        all = PackageManager.getClasses(IPostgreSQLView)
        for cls in all:
            if self.env.isComponentEnabled(cls):
                self._enableView(cls)
            elif hasattr(cls, 'view_id') and cls.view_id in self._view_objs:
                self._disableView(cls)
    
    def _enableView(self, cls):
        """
        Creates a SQL view by executing the returned SQL string directly.
        """
        # sanity checks
        try:
            verifyClass(IPostgreSQLView, cls)
        except Exception, e:
            msg = "Class %s has a wrong implementation of %s.\n%s"
            self.env.log.warn(msg % (cls, IPostgreSQLView, e))
            return
        # create view
        sql = cls(self.env).createView()
        name = cls.view_id
        try:
            self.env.db.createView(name, sql)
        except Exception, e:
            msg = "Could not create a SQL view defined by class %s.\n%s"
            self.env.log.error(msg % (cls, e.message))
            return
        # register
        self._view_objs[cls.view_id] = cls
    
    def _disableView(self, cls):
        try:
            self.env.db.dropView(cls.view_id)
        except Exception, e:
            msg = "Could not delete a SQL view defined by class %s.\n%s"
            self.env.log.error(msg % (cls, e.message))
            return
        # unregister
        self._view_objs.pop(cls.view_id)
    
    def get(self, url = None):
        """
        Returns a dictionary of activated SQL view classes.
        """
        return self._view_objs
    
    
class ProcessorIndexRegistry(object):
    """
    ProcessorIndex registry.
    """
    def __init__(self, env):
        self.env = env
    
    def update(self):
        """
        Refresh all ProcessorIndexes.
        """
        all = PackageManager.getClasses(IProcessorIndex)
        for cls in all:
            if self.env.isComponentEnabled(cls):
                self._enableProcessorIndex(cls)
            else:
                self._disableProcessorIndex(cls)
    
    def register(self, cls):
        """
        Register an IProcessorIndex.
        """
        # sanity checks
        try:
            verifyClass(IProcessorIndex, cls)
        except Exception, e:
            msg = "Class %s has a wrong implementation of %s.\n%s"
            self.env.log.warn(msg % (cls, IProcessorIndex, e))
            return
        rt = self.env.registry.db_getResourceType(cls.package_id,
                                                  cls.resourcetype_id)
        clsname = cls.__module__ + '.' + cls.__name__
        idx = index.XmlIndex(resourcetype = rt, xpath = "", 
                             type = index.PROCESSOR_INDEX,
                             options = clsname,
                             label = clsname)
        self.env.catalog.index_catalog.registerIndex(idx)
    
    def _enableProcessorIndex(self, cls):
        try:
            self.register(cls)
        except DuplicateObjectError, e:
            msg = "Skipping processor index %s: Index already exists.\n%s"
            self.env.log.info(msg % (cls, e))
            return
    
    def _disableProcessorIndex(self, cls):
        pass
