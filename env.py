# -*- coding: utf-8 -*-
"""
The one class to rule them all.

Environment is the base class to handle configuration, XML catalog, database 
and logging access.
"""

from seishub.auth import AuthenticationManager
from seishub.config import Configuration, Option, _TRUE_VALUES
from seishub.core import ComponentManager
from seishub.db.manager import DatabaseManager
from seishub.defaults import DEFAULT_COMPONENTS, HTTP_PORT
from seishub.loader import ComponentLoader
from seishub.log import Logger
from seishub.packages.installer import PackageInstaller
from seishub.processor import ResourceTree
from seishub.xmldb.xmlcatalog import XmlCatalog
from twisted.application import service
from twisted.internet import defer
import os
import sys
import time
# this line must be the last import - don't move!
from seishub.packages.registry import ComponentRegistry


__all__ = ['Environment']


class Environment(ComponentManager):
    """
    The one class to rule them all.
    
    Environment is the base class to handle configuration, XML catalog, 
    database and logging access.
    
    A SeisHub environment consists of:
        * a configuration handler env.config
        * a XML catalog handler env.catalog
        * a database handler env.db
        * a logging handler env.log
        * a package handler env.registry
        * a user management handler env.auth
    """
    
    Option('seishub', 'host', 'localhost', "Default host of this server.")
    
    def __init__(self, conf=None):
        """
        Initialize the SeisHub environment.
        """
        # set up component manager
        ComponentManager.__init__(self)
        self.compmgr = self
        # set a start up timestamp
        self.startup_time = int(time.time())
        # get SeisHub path
        path = self.getSeisHubPath()
        # set configuration handler
        if not conf or not isinstance(conf, Configuration):
            conf_file = os.path.join(path, 'conf', 'seishub.ini')
            self.config = Configuration(conf_file)
        else:
            self.config = conf
        self.config.path = path
        self.config.hubs = {}
        # set log handler
        self.log = Logger(self)
        # initialize all default options
        self.initDefaultOptions()
        # set up DB handler
        self.db = DatabaseManager(self) 
        # set XML catalog
        self.catalog = XmlCatalog(self)
        # user and group management
        self.auth = AuthenticationManager(self)
        # load plug-ins
        ComponentLoader(self)
        # Package manager
        # initialize ComponentRegistry after ComponentLoader(), as plug-ins may 
        # provide registry objects
        self.registry = ComponentRegistry(self)
        # trigger auto installer
        PackageInstaller.cleanup(self)
        # make sure SeisHub packages are installed first
        PackageInstaller.install(self, 'seishub')
        PackageInstaller.install(self)
        # initialize the resource tree
        self.tree = ResourceTree(self)
        self.update()
    
    def getSeisHubPath(self):
        """
        Returns the absolute path to the SeisHub directory.
        """
        import seishub
        return os.path.split(os.path.dirname(seishub.__file__))[0]
    
    def getRestUrl(self):
        """
        Returns the root URL of the REST pages.
        """
        rest_host = self.config.get('seishub', 'host') or 'localhost'
        rest_port = self.config.getint('http_port', 'port') or HTTP_PORT
        return 'http://'+ rest_host + ':' + str(rest_port)
    
    def update(self):
        """
        General update method after enabling/disabling components.
        """
        self.registry.mappers.update()
        self.registry.sqlviews.update()
        self.tree.update()
        self.registry.processor_indexes.update()
    
    @defer.inlineCallbacks
    def enableService(self, srv_name):
        """
        Enable a service.
        """
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
        """
        Disable a service.
        """
        for srv in service.IServiceCollection(self.app):
            if srv.name.lower()==srv_name.lower():
                self.config.set(srv.name.lower(), 'autostart', False)
                self.config.save()
                yield defer.maybeDeferred(srv.stopService)
                self.log.info('Stopping service %s.' % srv.name)
    
    def enableComponent(self, component):
        """
        Enables a component.
        """
        module = sys.modules[component.__module__]
        fullname = module.__name__+'.'+component.__name__
        if not component in self:
            self[component]
        self.enabled[component]=True
        self.config.set('components', fullname, 'enabled')
        self.config.save()
        # package installer must run first before saving
        if hasattr(component, 'package_id'):
            try:
                PackageInstaller.install(self, component.package_id)
            except Exception, e:
                self.disableComponent(component)
                return e.message
        self.log.info('Enabling component %s' % fullname)
        self.update()
    
    def disableComponent(self, component):
        """
        Disables a component.
        """
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
        PackageInstaller.cleanup(self)
        self.update()
    
    def initDefaultOptions(self):
        """
        Initialize any not yet set default options in configuration file.
        """
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
        """
        Initialize additional member variables for components.
        
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
        """
        Implemented to only allow activation of components that are not
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
        rules = sorted(rules, lambda a, b: -cmp(len(a[0]), len(b[0])))
        
        for pattern, state in rules:
            if pattern == classname.lower():
                return state
            if pattern == modulename.lower():
                return state
        return False
