# -*- coding: utf-8 -*-

import os

from seishub.core import ComponentManager
from seishub.config import Configuration, Option
from seishub.loader import ComponentLoader
from seishub.xmldb.xmlcatalog import XmlCatalog
from seishub.db.dbmanager import DatabaseManager
from seishub.log import Logger

__all__ = ['Environment']


class Environment(ComponentManager):
    """One class to rule them all: Enviroment is the base class to handle 
    configuration, xml catalog, database and logging access.
    
    A SeisHub environment consists of:
        * a configuration handler env.config
        * a xml catalog handler env.catalog
        * a database handler env.db
        * a logging handler env.log
    """   
    
    error_log_file = Option('logging', 'error_log_file', 'error.log',
        """If `log_type` is `file`, this should be a the name of the file.""")
    
    access_log_file = Option('logging', 'access_log_file', 'access.log',
        """If `log_type` is `file`, this should be a the name of the file.""")
    
    log_level = Option('logging', 'log_level', 'DEBUG',
        """Level of verbosity in log.
        
        Should be one of (`CRITICAL`, `ERROR`, `WARN`, `INFO`, `DEBUG`).""")
    
    def __init__(self):
        """Initialize the SeisHub environment."""
        # set up component manager
        ComponentManager.__init__(self)
        self.compmgr = self
        # set config handler
        self.config = Configuration()
        # set SeisHub path
        self.path = self.config.path
        # set log handler
        self.log = Logger(self)
        # set up db handler
        self.db = DatabaseManager(self) 
        # set xml catalog
        self.catalog = XmlCatalog(self.db)
        # load plugins
        ComponentLoader(self)
    
    def component_activated(self, component):
        """Initialize additional member variables for components.
        
        Every component activated through the `Environment` object gets five
        member variables: `env` (the environment object), `config` (the
        environment configuration), `log` (a logger object), `db` (the 
        database handler) and `catalog` (a xml catalog object)."""
        component.env = self
        component.config = self.config
        component.log = self.log
        component.db = self.db
        component.catalog = self.catalog
    
    def is_component_enabled(self, cls):
        """Implemented to only allow activation of components that are not
        disabled in the configuration.
        
        This is called by the `ComponentManager` base class when a component is
        about to be activated. If this method returns false, the component does
        not get activated."""
        if not isinstance(cls, basestring):
            component_name = (cls.__module__ + '.' + cls.__name__).lower()
        else:
            component_name = cls.lower()
        
        rules = [(name.lower(), value.lower() in ('enabled', 'on'))
                 for name, value in self.config.options('components')]
        rules.sort(lambda a, b: -cmp(len(a[0]), len(b[0])))
        
        for pattern, enabled in rules:
            if component_name == pattern or pattern.endswith('*') \
                    and component_name.startswith(pattern[:-1]):
                return enabled
        
        # By default, all components in the seishub package are enabled
        return component_name.startswith('seishub.')
