# -*- coding: utf-8 -*-

import os
import sqlalchemy as sa

from seishub.config import Option
from seishub.defaults import DEFAULT_DB_URI


meta = sa.MetaData()

SQLITE_WARNING = \
"""---------------------------------------------------------------
Warning: A SQLite database should never be used in a productive
environment! Instead try to use any supported database listed  
at http://www.sqlalchemy.org/trac/wiki/DatabaseNotes.          
---------------------------------------------------------------"""



class DatabaseManager(object):
    """A wrapper around SQLAlchemy connection pool."""
    
    Option('db', 'uri', DEFAULT_DB_URI, "Database URI.")
    Option('db', 'verbose', False, "Enables database verbosity.")
    
    pool_size = 5
    max_overflow = 10
    
    def __init__(self, env):
        self.version = sa.__version__
        self.env = env
        self.uri = self.env.config.get('db', 'uri')
        self.echo = self.env.config.getbool('db', 'verbose')
        self.engine = self._getEngine()
        self._initDb()
        self.env.log.info('DB connection pool started')
        
    def _initDb(self):
        self.metadata = meta
        self.metadata.bind = self.engine
        #this will check for the presence of a table first before creating
        self.metadata.create_all(self.engine, checkfirst = True)
    
    def _getEngine(self):
        if self.uri.startswith('sqlite:///'):
            #sqlite db
            filename =  self.uri[10:]
            filepart = filename.split('/')
            #it is a plain filename without sub directories
            if len(filepart)==1:
                self.uri = 'sqlite:///' + os.path.join(self.env.config.path, 
                                                       'db', filename)
                return self._getSQLiteEngine()
            #there is a db sub directory given in front of the filename
            if len(filepart)==2 and filepart[0]=='db':
                self.uri = 'sqlite:///' + os.path.join(self.env.config.path, 
                                                       filename)
                return self._getSQLiteEngine()
            #check if it is a full absolute file path
            if os.path.isdir(os.path.dirname(filename)):
                return self._getSQLiteEngine()
            #ok return a plain memory based database
            else:
                self.uri='sqlite://'
                return self._getSQLiteEngine()
        elif self.uri.startswith('sqlite://'):
            return self._getSQLiteEngine()
        
        return sa.create_engine(self.uri,
                                echo = self.echo,
                                encoding = 'utf-8',
                                convert_unicode = True,
                                max_overflow = self.max_overflow, 
                                pool_size = self.pool_size)
    
    def _getSQLiteEngine(self):
        """Return a sqlite engine without a connection pool."""
        
        logging =self.env.config.get('logging', 'log_level')
        
        if logging!='OFF':
            print SQLITE_WARNING
        
        return sa.create_engine(self.uri,
                                echo = self.echo,
                                encoding = 'utf-8',
                                convert_unicode = True,)

