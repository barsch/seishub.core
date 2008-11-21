# -*- coding: utf-8 -*-

import os
import sys
import time

from twisted.internet import defer
from twisted.application import service

from seishub.auth import AuthenticationManager
from seishub.core import ComponentManager
from seishub.config import Configuration, Option, _TRUE_VALUES
from seishub.loader import ComponentLoader
from seishub.packages.installer import PackageInstaller
from seishub.xmldb.xmlcatalog import XmlCatalog
from seishub.db.dbmanager import DatabaseManager
from seishub.log import Logger
from seishub.defaults import DEFAULT_COMPONENTS
from seishub.packages.registry import ComponentRegistry
from seishub.processor.resources import Site, FileSystemResource
from seishub.processor.resources import XMLRootFolder, MapperResource
#from seishub.processor.resources import XMLPackageFolder, XMLResourceTypeFolder, XMLResource

__all__ = ['Environment']


class Environment(ComponentManager):
    """One class to rule them all: Environment is the base class to handle
    configuration, XML catalog, database and logging access.
    
    A SeisHub environment consists of:
        * a configuration handler env.config
        * a XML catalog handler env.catalog
        * a database handler env.db
        * a logging handler env.log
        * a package handler env.registry
        * a user management handler env.auth
    """
    
    Option('seishub', 'host', 'localhost', 'Default host of this server.')
    
    def __init__(self, config_file=None):
        """Initialize the SeisHub environment."""
        # set up component manager
        ComponentManager.__init__(self)
        self.compmgr = self
        # set a start up timestamp
        self.startup_time = int(time.time())
        # get SeisHub path
        path = self.getSeisHubPath()
        if not config_file:
            config_file = os.path.join(path, 'conf', 'seishub.ini') 
        # set config handler
        self.config = Configuration(config_file)
        self.config.path = path
        self.config.hubs = {}
        # set log handler
        self.log = Logger(self)
        # init all default options
        self.initOptions()
        # set up DB handler
        self.db = DatabaseManager(self) 
        # set XML catalog
        self.catalog = XmlCatalog(self)
        # User & group management
        self.auth = AuthenticationManager(self)
        # load plugins
        ComponentLoader(self)
        # Package manager
        # init ComponentRegistry after ComponentLoader(), as plugins may 
        # provide registry objects
        self.registry = ComponentRegistry(self)
        # trigger auto installer, install seishub package first
        PackageInstaller.cleanup(self)
        # make sure seishub packages are installed first
        PackageInstaller.install(self, 'seishub')
        PackageInstaller.install(self)
        # initialize the resource tree
        self.updateResourceTree()
    
    def updateResourceTree(self):
        self.tree = Site()
        # set XML directory
        self.tree.addChild('xml', XMLRootFolder())
#        # demo - we shouldn't do that but it is possible
#        self.tree.addChild('/demo/1/package', XMLPackageFolder('seishub'))
#        self.tree.addChild('/demo/1/rt', XMLResourceTypeFolder('seishub','schema'))
#        self.tree.addChild('/demo/xml-root', XMLRootFolder())
#        self.tree.addChild('/demo/1/resource', XMLResource('seishub','stylesheet','1'))
        # set all mappings
        for url, cls in self.registry.mappers.get().items():
            self.tree.addChild(url, MapperResource(cls(self)))
        # set all file system folder
        for url, path in self.config.options('fs'):
            self.tree.addChild(url, FileSystemResource(path)) 
    
    def getSeisHubPath(self):
        """Returns the absolute path to the SeisHub directory."""
        import seishub
        return os.path.split(os.path.dirname(seishub.__file__))[0]
    
    def getRestUrl(self):
        """Returns the root URL of the REST pages."""
        rest_host = self.config.get('seishub', 'host')
        rest_port = self.config.getint('rest', 'port')
        return 'http://'+ str(rest_host) + ':' + str(rest_port)
    
    @defer.inlineCallbacks
    def enableService(self, srv_name):
        """Enable a service."""
        for srv in service.IServiceCollection(self.app):
            if srv.name.lower()==srv_name.lower():
                # ensure not to start a service twice; may be fatal with timers
                if srv.running:
                    self.log.info('Service %s already started.' % srv.name)
                    return
                self.config.set(srv.name.lower(), 'autostart', True)
                self.config.save()
                yield defer.maybeDeferred(srv.startService)
                self.log.info('Starting service %s.' % srv.name)
    
    @defer.inlineCallbacks
    def disableService(self, srv_name):
        """Disable a service."""
        for srv in service.IServiceCollection(self.app):
            if srv.name.lower()==srv_name.lower():
                self.config.set(srv.name.lower(), 'autostart', False)
                self.config.save()
                yield defer.maybeDeferred(srv.stopService)
                self.log.info('Stopping service %s.' % srv.name)
    
    def enableComponent(self, component):
        """Enables a component."""
        module = sys.modules[component.__module__]
        fullname = module.__name__+'.'+component.__name__
        if not component in self:
            self[component]
        self.enabled[component]=True
        self.config.set('components', fullname, 'enabled')
        self.log.info('Enabling component %s' % fullname)
        self.config.save()
        self.registry.mappers.update()
        if hasattr(component, 'package_id'):
            PackageInstaller.install(self, component.package_id)
    
    def disableComponent(self, component):
        """Disables a component."""
        module = sys.modules[component.__module__]
        fullname = module.__name__+'.'+component.__name__
        
        if fullname in DEFAULT_COMPONENTS:
            return
        
        if component in self:
            del self[component]
        self.enabled[component]=False
        self.config.set('components', fullname, 'disabled')
        self.log.info('Disabling component %s' % fullname)
        self.config.save()
        self.registry.mappers.update()
        PackageInstaller.cleanup(self)
    
    def initOptions(self):
        """Initialize any not yet set default options in configuration file."""
        defaults = self.config.defaults()
        for section in defaults.keys():
            for name in defaults.get(section).keys():
                if self.config.has_site_option(section, name):
                    continue
                else:
                    value = defaults.get(section).get(name)
                    self.config.set(section, name, value)
                    self.log.info('Setting default value for [%s] %s = %s' \
                                  % (section, name, value))
                    self.config.save()
    
    def initComponent(self, component):
        """Initialize additional member variables for components.
        
        Every component activated through the `Environment` object gets a few
        member variables: `env` (the environment object), `config` (the
        environment configuration), `log` (a logger object), `db` (the 
        database handler), `catalog` (a XML catalog object), `registry` (a 
        package registry handler) and `auth` (a user management object).
        """
        component.env = self
        component.config = self.config
        component.log = self.log
        component.db = self.db
        component.catalog = self.catalog
        component.registry = self.registry
        component.auth = self.auth
    
    def isComponentEnabled(self, cls):
        """Implemented to only allow activation of components that are not
        disabled in the configuration.
        
        This is called by the `ComponentManager` base class when a component is
        about to be activated. If this method returns false, the component does
        not get activated.
        """
        if isinstance(cls, basestring):
            modulename = '.'.join(cls.split('.')[:-1])
            classname = cls
        else:
            modulename = cls.__module__
            classname = modulename + '.' + cls.__name__
        
        # all default components are enabled
        if classname in DEFAULT_COMPONENTS:
            return True
        if modulename in DEFAULT_COMPONENTS:
            return True
        
        # parse config file and return state of either class or module
        rules = [(name, value in _TRUE_VALUES)
                 for name, value in self.config.options('components')]
        rules.sort(lambda a, b: -cmp(len(a[0]), len(b[0])))
        
        for pattern, state in rules:
            if pattern == classname.lower():
                return state
            if pattern == modulename.lower():
                return state
        return False