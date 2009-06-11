# -*- coding: utf-8 -*-

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
        search_path = [plugins_dir, ]
        # add user defined paths
        if extra_path:
            search_path += list((extra_path,))
        self._loadEggs('seishub.plugins', search_path)

    def _loadEggs(self, entry_point, search_path):
        """
        Loader that loads SeisHub eggs from the search path and L{sys.path}.
        """
        self.env.log.debug('Looking for plug-ins ...')
        # add system paths
        search_path += list(sys.path)

        distributions, errors = pkg_resources.working_set.find_plugins(
            pkg_resources.Environment(search_path)
        )
        for d in distributions:
            # lookup entry points
            if entry_point not in d.get_entry_map().keys():
                continue
            self.env.log.debug('Found egg %s ...' % (d))
            pkg_resources.working_set.add(d)

        for dist, e in errors.iteritems():
            self.env.log.error('Skipping egg "%s": %s' % (dist, e))

        for entry in pkg_resources.iter_entry_points(entry_point):
            self.env.log.debug('Initialize egg %s ...' % (entry.module_name))
            try:
                entry.load()
            except Exception, e:
                self.env.log.error('Skipping egg "%s": %s' % (entry.name, e))
        self.env.log.info('Plug-ins have been initialized.')
