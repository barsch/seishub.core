# -*- coding: utf-8 -*-

import sqlalchemy as sa

from seishub.defaults import DEFAULT_DB_URI


class DatabaseManager(object):
    """A wrapper around SQLAlchemy connection pool."""
    
    pool_size = 5
    max_overflow = 10
    
    def __init__(self, env):
        self.env = env
        self.uri = self.env.config.get('seishub', 'database') or DEFAULT_DB_URI
        self.engine = self._getEngine()
        self.metadata = None 
        self.env.log.info('DB connection pool started')
    
    def _getEngine(self):
        return sa.create_engine(self.uri,
                                echo = True,
                                encoding = 'utf-8',
                                convert_unicode = True,)
                                #max_overflow = self.max_overflow, 
                                #pool_size = self.pool_size)
    
    def _checkVersion(self):
        self.version = sa.__version__
        if not self.version.startswith('0.4'):
            self.env.log.error("We need at least a SQLAlchemy 0.4.0")
