# -*- coding: utf-8 -*-
"""
The database manager.
"""

from seishub.core.config import Option, IntOption
from seishub.core.db import DEFAULT_MAX_OVERFLOW, DEFAULT_POOL_SIZE, \
    DEFAULT_DB_URI
from seishub.core.db.util import compileStatement
from seishub.core.exceptions import NotFoundError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
import os
import sqlalchemy as sa


meta = sa.MetaData()


class DatabaseManager(object):
    """
    A wrapper around the SQLAlchemy connection pool.
    """
    Option('db', 'uri', DEFAULT_DB_URI, "Database URI.")
    Option('db', 'verbose', False, "Enables database verbosity.")
    IntOption('db', 'max_overflow', DEFAULT_MAX_OVERFLOW,
        "The number of connections to allow in connection pool 'overflow', "
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
        self.session = sessionmaker(bind=self.engine)
        self.env.log.info('DB connection pool started')

    def _initDb(self):
        """
        Initialize the database.
        """
        self.metadata = meta
        self.metadata.bind = self.engine
        # we need to filter tables - otherwise vies are generated as tables too
        tables = [t for t in self.metadata.tables.values()
                  if not t.name.startswith('/')]
        # this will check for the presence of a table first before creating
        try:
            self.metadata.create_all(self.engine, tables=tables,
                                     checkfirst=True)
        except sa.exceptions.DBAPIError, e:
            print("ERROR:  %s" % str(e.orig))
            quit()

    def _getEngine(self):
        """
        Creates an database engine by processing self.uri.
        """
        if self.uri.startswith('sqlite:///'):
            # we got someSQLite database
            filename = self.uri[10:]
            filepart = filename.split('/')
            # it is a plain filename without sub directories
            if len(filepart) == 1:
                self.uri = 'sqlite:///' + \
                    os.path.join(self.env.getInstancePath(), 'db', filename)
                return self._getSQLiteEngine()
            # there is a db sub directory given in front of the filename
            if len(filepart) == 2 and filepart[0] == 'db':
                self.uri = 'sqlite:///' + \
                    os.path.join(self.env.getInstancePath(), filename)
                return self._getSQLiteEngine()
            # check if it is a full absolute file path
            if os.path.isdir(os.path.dirname(filename)):
                return self._getSQLiteEngine()
            # ok return a plain memory based database
            else:
                self.uri = 'sqlite://'
                return self._getSQLiteEngine()
        elif self.uri.startswith('sqlite://'):
            return self._getSQLiteEngine()

        return sa.create_engine(self.uri,
                                echo=self.echo,
                                encoding='utf-8',
                                convert_unicode=True,
                                max_overflow=self.max_overflow,
                                pool_size=self.pool_size,
                                pool_recycle=3600,
                                )

    def _getSQLiteEngine(self):
        """
        Return a SQLite engine without a connection pool.
        """
        # warn if using SQLite as database
        self.env.log.warn("A SQLite database should never be used in a "
                          "productive environment!")
        # create engine
        return sa.create_engine(self.uri,
                                echo=self.echo,
                                encoding='utf-8',
                                convert_unicode=True)

    def query(self, *args, **kwargs):
        """
        Shortcut for querying the database.
        """
        return self.engine.execute(*args, **kwargs)

    def createView(self, name, query):
        """
        Create a SQL view from a query and a view name.
        """
        try:
            self.dropView(name)
        except NotFoundError:
            pass
        name = self.engine.dialect.identifier_preparer.quote_identifier(name)
        if not isinstance(query, basestring):
            # keep it backwards compatible for SQLViewRegistry
            # (is this used at all ?)
            self.env.log.warn('compileStatement should not be used for views!')
            query = compileStatement(query)
        sql = "CREATE VIEW %s AS %s" % (name, query)
        self.engine.execute(sql)

    def dropView(self, name):
        """
        Drop a SQL view by its name.
        """
        name = self.engine.dialect.identifier_preparer.quote_identifier(name)
        sql = "DROP VIEW %s" % name
        if self.engine.name.startswith('postgres'):
            sql += ' CASCADE'
        try:
            self.engine.execute(sql)
        except Exception:
            msg = "A view with the name %s does not exist."
            raise NotFoundError(msg % name)

    def dropAllViews(self):
        """
        Drop all SQL views from database.
        """
        views = self.getViews()
        for name in views:
            self.dropView(name)

    def getViews(self):
        """
        Get all SQL Views from database.
        """
        if self.engine.name == 'sqlite':
            sql = "SELECT name from sqlite_master WHERE type='view';"
            temp = self.engine.execute(sql).fetchall()
            return [id[0] for id in temp]
        elif self.engine.name.startswith('postgres'):
            sql = """SELECT viewname FROM pg_views
                     WHERE schemaname
                     NOT IN('information_schema', 'pg_catalog');"""
            temp = self.engine.execute(sql).fetchall()
            return [id[0] for id in temp]
        return []

    def getTableSize(self, name):
        """
        Returns the size of a database table or view.
        """
        if self.engine.name.startswith('postgres'):
            sql = "SELECT pg_relation_size('%s');" % name
            result = self.engine.execute(sql).fetchall()[0]
            return result[0]
        return None

    def getDatabaseSize(self):
        """
        Returns the size of the whole database.
        """
        if self.engine.name.startswith('postgres'):
            # XXX: Only works for pg yet
            sql = "SELECT pg_database_size('%s');" % self.engine.url.database
            result = self.engine.execute(sql).fetchall()[0]
            return result[0]
        return None

    def isSQLite(self):
        """
        Return True if a SQLite database is used.
        """
        return self.engine.name.lower() == 'sqlite'
