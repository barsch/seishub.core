# -*- coding: utf-8 -*-

import os

from seishub.core import ComponentManager
from seishub.config import Configuration, Option
from seishub.loader import loadComponents
from seishub.xmldb.xmlcatalog import XmlCatalog

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
    
    log_type = Option('logging', 'log_type', 'none',
        """Logging facility to use.
        
        Should be one of (`none`, `file`, `stderr`, `syslog`, `winlog`).""")
    
    log_file = Option('logging', 'log_file', 'seishub.log',
        """If `log_type` is `file`, this should be a path to the log-file.""")
    
    log_level = Option('logging', 'log_level', 'DEBUG',
        """Level of verbosity in log.
        
        Should be one of (`CRITICAL`, `ERROR`, `WARN`, `INFO`, `DEBUG`).""")
    
    log_format = Option('logging', 'log_format', None,
        """Custom logging format.
        
        If nothing is set, the following will be used:
        
        SeisHub[$(module)s] $(levelname)s: $(message)s
        
        In addition to regular key names supported by the Python logger library
        library (see http://docs.python.org/lib/node422.html), one could use:
         - $(path)s     the path for the current environment
         - $(basename)s the last path component of the current environment
         - $(project)s  the project name
        
        Note the usage of `$(...)s` instead of `%(...)s` as the latter form
        would be interpreted by the ConfigParser itself.
        
        Example:
        ($(thread)d) Trac[$(basename)s:$(module)s] $(levelname)s: $(message)s
        
        """)
    
    def __init__(self):
        """Initialize the SeisHub environment."""
        ComponentManager.__init__(self)
        self.compmgr = self
        
        # set config handler
        self.config = Configuration()
        
        # set SeisHub path
        import seishub
        self.path = os.path.split(os.path.dirname(seishub.__file__))[0]
        
        # set log handler
        self.setupLogging()
        
        # set xml catalog
        self.catalog = XmlCatalog(self)
        
        plugins_dir = self.config.get('seishub', 'plugins_dir')
        loadComponents(self, plugins_dir and (plugins_dir,))
    
    def component_activated(self, component):
        """Initialize additional member variables for components.
        
        Every component activated through the `Environment` object gets three
        member variables: `env` (the environment object), `config` (the
        environment configuration) and `log` (a logger object)."""
        component.env = self
        component.config = self.config
        component.log = self.log
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
    
    def setupLogging(self):
        """Initialize the logging sub-system."""
        from seishub.log import logger_factory
        logtype = self.log_type
        logfile = self.log_file
        logdir = os.path.join(self.path, 'log')
        if logtype == 'file' and not os.path.isabs(logfile):
            logfile = os.path.join(logdir, logfile)
        format = self.log_format
        if format:
            format = format.replace('$(', '%(') \
                     .replace('%(path)s', self.path) \
                     .replace('%(basename)s', os.path.basename(self.path)) \
                     .replace('%(project)s', self.project_name)
        self.log = logger_factory(logtype, logfile, self.log_level, self.path,
                                  format=format)
