# -*- coding: utf-8 -*-

from seishub.config import Option, IntOption
from seishub.db import DEFAULT_MAX_OVERFLOW, DEFAULT_POOL_SIZE, DEFAULT_DB_URI, \
    util
from seishub.exceptions import NotFoundError
import os
import sqlalchemy as sa


meta = sa.MetaData()


class DatabaseManager(object):
    """
    A wrapper around SQLAlchemy connection pool.
    """
    Option('db', 'uri', DEFAULT_DB_URI, "Database URI.")
    Option('db', 'verbose', False, "Enables database verbosity.")
    IntOption('db', 'max_overflow', DEFAULT_MAX_OVERFLOW, 
        "The number of connections to allow in connection pool “overflow”, "
        "that is connections that can be opened above and beyond the " +
        "pool_size setting, which defaults to five.")
    IntOption('db', 'pool_size', DEFAULT_POOL_SIZE, 
        "The number of connections to keep open inside the connection pool.")
    
    def __init__(self, env):
        self.version = sa.__version__
        self.env = env
        self.uri = self.env.config.get('db', 'uri')
        self.echo = self.env.config.getbool('db', 'verbose')
        self.max_overflow = self.env.config.getint('db', 'max_overflow') or \
            DEFAULT_MAX_OVERFLOW
        self.pool_size = self.env.config.getint('db', 'pool_size') or \
            DEFAULT_POOL_SIZE
        self.engine = self._getEngine()
        self._initDb()
        self.env.log.info('DB connection pool started')
    
    def _initDb(self):
        """
        Initialize the database.
        """
        self.metadata = meta
        self.metadata.bind = self.engine
        #this will check for the presence of a table first before creating
        self.metadata.create_all(self.engine, checkfirst = True)
    
    def _getEngine(self):
        """
        Creates an database engine by processing self.uri.
        """
        if self.uri.startswith('sqlite:///'):
            # we got someSQLite database
            filename =  self.uri[10:]
            filepart = filename.split('/')
            # it is a plain filename without sub directories
            if len(filepart)==1:
                self.uri = 'sqlite:///' + os.path.join(self.env.config.path, 
                                                       'db', filename)
                return self._getSQLiteEngine()
            # there is a db sub directory given in front of the filename
            if len(filepart)==2 and filepart[0]=='db':
                self.uri = 'sqlite:///' + os.path.join(self.env.config.path, 
                                                       filename)
                return self._getSQLiteEngine()
            # check if it is a full absolute file path
            if os.path.isdir(os.path.dirname(filename)):
                return self._getSQLiteEngine()
            # ok return a plain memory based database
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
        """
        Return a SQLite engine without a connection pool.
        """
        # warn if using SQLite as database
        self.env.log.warn("A SQLite database should never be used in a "
                          "productive environment!")
        # create engine
        return sa.create_engine(self.uri, 
                                echo = self.echo,
                                encoding = 'utf-8', 
                                convert_unicode = True)
    
    def createView(self, name, query):
        try:
            self.dropView(name)
        except NotFoundError:
            pass
        sql = 'CREATE VIEW "%s" AS %s' % (name, util.compileStatement(query))
        self.engine.execute(sql)
    
    def dropView(self, name):
        sql = 'DROP VIEW "%s"' % name
        if self.engine.name == 'postgres':
            sql += ' CASCADE';
        try:
            self.engine.execute(sql)
        except Exception:
            msg = "A view with the name %s does not exist."
            raise NotFoundError(msg % name)
    
    def getViews(self):
        if self.engine.name == 'sqlite':
            sql = "SELECT name from sqlite_master WHERE type='view';"
            temp = self.engine.execute(sql).fetchall()
            return [id[0] for id in temp]
        elif self.engine.name == 'postgres':
            sql = """SELECT viewname FROM pg_views 
                     WHERE schemaname 
                     NOT IN('information_schema', 'pg_catalog');"""
            temp = self.engine.execute(sql).fetchall()
            return [id[0] for id in temp]
        return []