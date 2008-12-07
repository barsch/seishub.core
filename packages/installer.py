import sys, os

from seishub.exceptions import SeisHubError
from seishub.xmldb.xmlcatalog import INDEX_TYPES

class PackageInstaller(object):
    """The PackageInstaller allows file system based registration of:
     * packages
     * resource types
     * schemas
     * stylesheets
     * aliases
     * indexes
      
    A package/resourcetype etc. is installed automatically when found the 
    first time, but not if an already existing package was updated to a new
    version. To find out about updated packages and resourcetypes use 
    the getUpdated() method.
    """
    
    @staticmethod
    def _install_package(env, p):
        if hasattr(p, 'version'):
            version = p.version
        else:
            version = ''
        env.registry.db_registerPackage(p.package_id, version)
    
    @staticmethod
    def _install_resourcetype(env, rt):
        if hasattr(rt, 'version'):
            version = rt.version
        else:
            version = ''
        if hasattr(rt, 'version_control'):
            version_control = rt.version_control
        else:
            version_control = False
        env.registry.db_registerResourceType(rt.package_id,
                                             rt.resourcetype_id,
                                             version,
                                             version_control)

    @staticmethod
    def _install_pre_registered(env, o):
        package_id = o.package_id
        resourcetype_id = None
        if hasattr(o, 'resourcetype_id'):
            resourcetype_id = o.resourcetype_id
        if hasattr(o, '_registry_schemas'):
            for entry in o._registry_schemas:
                type = entry['type']
                # check, if already there
                if env.registry.schemas.get(package_id, resourcetype_id, type):
                    env.log.info("'%s': Skipping schema '%s'." % \
                                 (package_id, entry))
                    continue
                try:
                    data = file(entry['filename'], 'r').read()
                    env.registry.schemas.register(package_id, 
                                                  resourcetype_id, 
                                                  type, data)
                    env.log.info("'%s': Registered schema '%s'." % \
                                 (package_id, entry))
                except Exception, e:
                    env.log.warn(("Registration of schema failed: " +\
                                 "%s (%s)") % (entry['filename'] ,e))
        
        if hasattr(o, '_registry_stylesheets'):
            for entry in o._registry_stylesheets:
                type = entry['type']
                # check, if already there
                if env.registry.stylesheets.get(package_id, resourcetype_id, 
                                                type):
                    env.log.info("'%s': Skipping stylesheet '%s'." %\
                                 (package_id, entry))
                    continue
                try:
                    data = file(entry['filename'], 'r').read()
                    env.registry.stylesheets.register(package_id, 
                                                      resourcetype_id, 
                                                      type, data)
                    env.log.info("'%s': Registered stylesheet '%s'." %\
                                 (package_id, entry))
                except Exception, e:
                    env.log.warn(("Registration of stylesheet failed: " +\
                                 "%s (%s)") % (entry['filename'], e))
                    
        if hasattr(o, '_registry_aliases'):
            for entry in o._registry_aliases:
                # check, if already there
                if env.registry.aliases.get(package_id, resourcetype_id, 
                                            **entry):
                    env.log.info("'%s': Skipping alias '%s'." %\
                                 (package_id, entry))
                    continue
                try:
                    env.registry.aliases.register(package_id, 
                                                  resourcetype_id,
                                                  **entry)
                    env.log.info("'%s': Registered alias '%s'." %\
                                 (package_id, entry))
                except Exception, e:
                    env.log.warn(("Registration of alias failed: " +\
                                 "%s/%s/@%s (%s)") %\
                                (package_id, resourcetype_id, entry['name'], 
                                 e))

        if hasattr(o, '_registry_indexes'):
            for entry in o._registry_indexes:
                # check, if already there
                if env.catalog.getIndex(package_id, resourcetype_id, **entry):
                    # idx_type = [typestr for typestr, id in INDEX_TYPES.iteritems() if id == entry['type']][0]
                    env.log.info("'%s': Skipping index '%s'." %\
                                 (package_id, entry))
                    continue
                try:
                    env.catalog.registerIndex(package_id, 
                                              resourcetype_id,
                                              **entry)
                    env.log.info("'%s': Registered index '%s'." %\
                                 (package_id, entry))
                except Exception, e:
                    env.log.warn(("Registration of index failed: " +\
                                 "/%s/%s%s (%s)") %\
                                (package_id, resourcetype_id, entry['xpath'], 
                                 e))
                    
    @staticmethod
    def _pre_register(*args, **kwargs):
        """pre-register an object from filesystem"""
        reg = args[0]
        # get package id and resourcetype_id from calling class
        frame = sys._getframe(2)
        locals_ = frame.f_locals
        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'registerStylesheet() can only be used in a class definition'
        package_id = locals_.get('package_id', None)
        resourcetype_id = locals_.get('resourcetype_id', None)
        assert package_id, 'class must provide package_id'
        if reg in ['_schemas', '_indexes']:
            assert resourcetype_id, 'class must provide resourcetype_id'
        # relative path -> absolute path
        filename = kwargs.get('filename', None)
        if filename:
            kwargs['filename'] = os.path.join(os.path.dirname(
                                           frame.f_code.co_filename), filename)
        locals_.setdefault('_registry' + reg, []).append(kwargs)
            
    @staticmethod
    def install(env, package_id = None):
        """auto install all known packages
        if package is given, only the specified package will be installed"""
        # XXX: problem: if installation fails here, packages still show up in the
        # registry but adding of resources etc. is not possible => possible solution
        # mark those packages as 'defect' and handle that seperately in the admin interface
        if package_id:
            packages = [package_id]
        else:
            packages = env.registry.getPackageIds()
        # install new packages
        for p in packages:
            fs_package = env.registry.getPackage(p)
            db_packages = env.registry.db_getPackages(p)
            # if package not in database yet, add it
            if len(db_packages) == 0:
                try:
                    PackageInstaller._install_package(env, fs_package)
                except Exception, e:
                    env.log.warn(("Registration of package with id '%s' "+\
                                  "failed. (%s)") % (p, e))
                    continue
            # (re)install package specific objects
            PackageInstaller._install_pre_registered(env, fs_package)
                
            # install new resourcetypes for package p
            for rt in env.registry.getResourceTypes(p):
                db_rt = env.registry.db_getResourceTypes(p, rt.resourcetype_id)
                if len(db_rt) == 0:
                    try:
                        PackageInstaller._install_resourcetype(env, rt)
                    except Exception, e:
                        env.log.warn(("Registration of resourcetype "+\
                                      "with id '%s' in package '%s'"+\
                                      " failed. (%s)") % \
                                      (rt.resourcetype_id, p, e))
                        continue
                # (re)install resourcetype specific objects
                PackageInstaller._install_pre_registered(env, rt)

    @staticmethod        
    def cleanup(env):
        """automatically remove unused packages"""
        # XXX: see ticket #74
        return
        db_rtypes = env.registry.db_getResourceTypes()
        for rt in db_rtypes:
            # XXX: check if referenced elsewhere!!!
            if [rt.package.package_id, rt.resourcetype_id] not in \
               [[o.package_id, o.resourcetype_id] for o in env.registry.getResourceTypes(rt.package.package_id)]:
                try:
                    env.registry.db_deleteResourceType(rt.package.package_id, 
                                                       rt.resourcetype_id)
                except SeisHubError:
                    pass
        db_packages = env.registry.db_getPackages()
        fs_packages = env.registry.getPackageIds()
        for p in db_packages:
            if p.package_id not in fs_packages:
                try:
                    env.registry.db_deletePackage(p.package_id)
                except SeisHubError:
                    pass

    @staticmethod
    def getUpdatedPackages():
        pass

    @staticmethod
    def getUpdatedResourcetypes(package_id = None):
        pass

registerSchema = lambda type, filename: \
                    PackageInstaller._pre_register('_schemas', 
                                                   type = type,
                                                   filename = filename)
registerStylesheet = lambda type, filename: \
                    PackageInstaller._pre_register('_stylesheets', 
                                                   type = type,
                                                   filename = filename)
registerAlias = lambda name, expr, limit = None, order_by = None: \
                    PackageInstaller._pre_register('_aliases',
                                                   name = name,
                                                   expr = expr,
                                                   limit = limit,
                                                   order_by = order_by)
registerIndex = lambda xpath, type = 'text', options = None: \
                    PackageInstaller._pre_register('_indexes',
                                                   xpath = xpath,
                                                   type = type,
                                                   options = options)
