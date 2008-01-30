# -*- coding: utf-8 -*-

import weakref
import re
from twisted.enterprise import adbapi

from seishub.defaults import DEFAULT_DB_URI


class DatabaseManager():
    """A Database Manager to handle a few common databases."""
    
    def __init__(self, env):
        #XXX: maybe we should go for weak env references in all objects below env 
        #otherwise destructurs are never called (cyclic references)
        self.env = weakref.proxy(env)
        self.uri = self.env.config.get('seishub','database') or DEFAULT_DB_URI
        self.driver = self.selectDatabaseDriver()
        self.db_args=self.getDbArgs()
        self.connection_pool=self.setupConnectionPool()
        
    def selectDatabaseDriver(self):
        if self.uri.startswith('mysql:'):
            return 'MySQLdb'
        elif self.uri.startswith('postgres:'):
            return 'pyPgSQL.PgSQL'
        elif self.uri.startswith('sqlite:'):
            return 'sqlite3'
        else:
        # use a temporary sqlite database - will be in memory only!!! 
            self.uri = ':memory:'
            return 'sqlite3'
        
    def getDbArgs(self):
        pattern="[^:/@]+"    
        r=re.compile(pattern)
        res=r.findall(self.uri)
        if res[0]=='postgres':
            return {'host':res[3],
                    'port':res[4],
                    'database':res[5],
                    'user':res[1],
                    'password':res[2]}
        else:
            return dict()
        
    def setupConnectionPool(self):
        return adbapi.ConnectionPool(self.driver, **self.db_args)

