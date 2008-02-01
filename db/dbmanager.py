# -*- coding: utf-8 -*-

import re
from twisted.enterprise import adbapi

from seishub.defaults import DEFAULT_DB_URI


class DatabaseManager(object):
    """A Database Manager to handle a few common databases."""
    
    def __init__(self, env):
        self.env = env
        self.uri = self.env.config.get('seishub','database') or DEFAULT_DB_URI
        self.driver = self.selectDatabaseDriver()
        self.db_args=self.getDbArgs()
        self.connection_pool=self.setupConnectionPool()
        self.env.log.info('DB connection pool started')
    
    def selectDatabaseDriver(self):
        if self.uri.startswith('mysql://'):
            return 'MySQLdb'
        elif self.uri.startswith('postgres://'):
            return 'pyPgSQL.PgSQL'
        elif self.uri.startswith('sqlite://'):
            return 'sqlite3'
        else:
            # use a temporary sqlite database - will be in memory only!!! 
            self.uri = 'sqlite://:memory:'
            return 'sqlite3'
    
    def getDbArgs(self):
        pattern="[^:/@]+"    
        r=re.compile(pattern)
        res=r.findall(self.uri)
        if res[0]=='postgres' or res[0]=='mysql':
            return {'host':res[3],
                    'port':res[4],
                    'database':res[5],
                    'user':res[1],
                    'password':res[2]}
        else:
            return {'database': self.uri[9:]}
    
    def setupConnectionPool(self):
        cp=adbapi.ConnectionPool(self.driver, **self.db_args)
        cp.noisy = True
        return cp
