# -*- coding: utf-8 -*-

from glob import glob
import imp
import os
import pkg_resources #@UnresolvedImport
import sys


__all__ = ['ComponentLoader']


class ComponentLoader(object):
    """
    Load all external plug-ins found on the given search path.
    """
    
    def __init__(self, env):
        self.env = env
        extra_path = env.config.get('seishub', 'plugins_dir')
        # add plug-in directory
        plugins_dir = os.path.join(env.config.path, 'plugins')
        search_path = [plugins_dir,]
        # add user defined paths
        if extra_path:
            search_path += list((extra_path,))
        
        self._loadPyFiles(search_path)
        self._loadEggs('seishub.plugins', search_path)
    
    def _loadEggs(self, entry_point, search_path):
        """
        Loader that loads any eggs on the search path and L{sys.path}.
        """
        # add system paths
        search_path += list(sys.path)
        
        distributions, errors = pkg_resources.working_set.find_plugins(
            pkg_resources.Environment(search_path)
        )
        for d in distributions:
            self.env.log.debug('Processing egg %s from %s' % (d, d.location))
            pkg_resources.working_set.add(d)
        
        for dist, e in errors.iteritems():
            self.env.log.error('Skipping "%s": %s' % (dist, e))
        
        for entry in pkg_resources.working_set.iter_entry_points(entry_point):
            self.env.log.info('Loading egg %s from %s' % (entry.name,
                              entry.dist.location))
            try:
                entry.load(require=True)
            except Exception, e:
                self.env.log.error('Skipping "%s": %s' % (entry.name, e))
    
    def _loadPyFiles(self, search_path):
        """
        Loader that look for Python source files in the plug-in directories.
        
        Source file will be imported, thereby registering them with the 
        component manager if they define any components.
        """
        for path in search_path:
            plugin_files = glob(os.path.join(path, '*'))
            for plugin_file in plugin_files:
                if not os.path.isdir(plugin_file):
                    continue
                try:
                    plugin_name = os.path.basename(plugin_file)
                    plugin_file += os.sep+'__init__.py'
                    msg = "Loading plug-in %s from %s"
                    self.env.log.info(msg % (plugin_name, plugin_file))
                    if plugin_name not in sys.modules:
                        imp.load_source(plugin_name, plugin_file)
                except Exception, e:
                    msg = "Failed to load plug-in from %s" % (plugin_file)
                    self.env.log.error(msg, e)
