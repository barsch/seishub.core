# -*- coding: utf-8 -*-

from seishub.defaults import DEFAULT_DB_URI


class DatabaseManager():
    """A Database Manager to handle a few common databases."""
    
    def __init__(self, env):
        self.env = env
        self.uri = self.env.config.get('seishub','database') or DEFAULT_DB_URI
        self.driver = self.selectDatabaseDriver()
        
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

