# -*- coding: utf-8 -*-

from glob import glob
import imp
import os
import pkg_resources #@UnresolvedImport
import sys


__all__ = ['ComponentLoader']


class ComponentLoader(object):
    """
    Load all plug-ins found on the given search path.
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
            self.env.log.debug('Processing egg %s ...' % (d))
            pkg_resources.working_set.add(d)
        
        for dist, e in errors.iteritems():
            self.env.log.error('Skipping "%s": %s' % (dist, e))
        
        for entry in pkg_resources.working_set.iter_entry_points(entry_point):
            self.env.log.info('Loading egg %s ...' % (entry.module_name))
            try:
                entry.load(require=True)
            except Exception, e:
                self.env.log.error('Skipping "%s": %s' % (entry.name, e))
