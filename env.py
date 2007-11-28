# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2005 Edgewall Software
# Copyright (C) 2003-2005 Jonas Borgström <jonas@edgewall.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>

import os
from sqlalchemy import create_engine

from seishub.config import Option

__all__ = ['Environment']


class Environment():
    """SeisHub stores project information in a Seishub environment.

    A SeisHub environment consists of a directory structure containing among 
    other things:
        * a configuration file.
        * a SQL database handler
    """   
    
    base_url = Option('seishub', 'base_url', '',
        """Base URL of the SeisHub deployment.
        
        In most configurations, SeisHub will automatically reconstruct the URL
        that is used to access it automatically. However, in more complex
        setups, usually involving running SeisHub behind a HTTP proxy, you may
        need to use this option to force SeisHub to use the correct URL.""")

    log_type = Option('logging', 'log_type', 'none',
        """Logging facility to use.
        
        Should be one of (`none`, `file`, `stderr`, `syslog`, `winlog`).""")

    log_file = Option('logging', 'log_file', 'trac.log',
        """If `log_type` is `file`, this should be a path to the log-file.""")


    def __init__(self, path, create=False, options=[]):
        """Initialize the Trac environment.
        
        @param path:    the absolute path to the Trac environment
        @param create:  if `True`, the environment is created and populated 
                        with default data; otherwise, the environment is 
                        expected to already exist.
        @param options: A list of `(section, name, value)` tuples that define
                        configuration options
        """

        self.path = path

#        from seishub.loader import load_components
#        load_components(self)

#    def get_db_cnx(self):
#       """Return a database connection from the connection pool."""
#        return DatabaseManager(self).get_connection()

#   def shutdown(self, tid=None):
#        """Close the environment."""
#        DatabaseManager(self).shutdown(tid)

