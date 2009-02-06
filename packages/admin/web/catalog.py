# -*- coding: utf-8 -*-
"""
Catalog and database related administration panels.
"""

from seishub.core import Component, implements
from seishub.db import DEFAULT_PREFIX, DEFAULT_POOL_SIZE, DEFAULT_MAX_OVERFLOW
from seishub.exceptions import SeisHubError, InvalidParameterError
from seishub.packages.interfaces import IAdminPanel
from sqlalchemy import create_engine #@UnresolvedImport
import os


class BasicPanel(Component):
    """
    Database configuration.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'catalog_db_basic.tmpl'
    panel_ids = ('catalog', 'Catalog', 'db-basic', 'Database Settings')
    has_roles = ['CATALOG_ADMIN']
    
    def render(self, request):
        db = self.db
        data = {
          'db': db,
          'uri': self.config.get('db', 'uri'),
          'pool_size': self.config.getint('db', 'pool_size'),
          'max_overflow': self.config.getint('db', 'max_overflow'),
        }
        if db.engine.name=='sqlite':
            data['info'] = ("SQLite Database enabled!", "A SQLite database "
                            "should never be used in a productive "
                            "environment!<br />Instead try to use any "
                            "supported database listed at "
                            "<a href='http://www.sqlalchemy.org/trac/wiki/"
                            "DatabaseNotes'>http://www.sqlalchemy.org/trac/"
                            "wiki/DatabaseNotes</a>.")
        if request.method == 'POST':
            uri = request.args.get('uri',[''])[0]
            pool_size = request.args.get('pool_size' ,[DEFAULT_POOL_SIZE])[0]
            max_overflow = request.args.get('max_overflow',
                                            [DEFAULT_MAX_OVERFLOW])[0]
            verbose = request.args.get('verbose',[False])[0]
            self.config.set('db', 'verbose', verbose)
            self.config.set('pool_size', 'pool_size', pool_size)
            self.config.set('max_overflow', 'max_overflow', max_overflow)
            data['uri'] = uri
            try:
                engine = create_engine(uri)
                engine.connect()
            except:
                data['error'] = ("Could not connect to database %s" % uri, 
                                 "Please make sure the database URI has " + \
                                 "the correct syntax: dialect://user:" + \
                                 "password@host:port/dbname.")
            else:
                self.config.set('db', 'uri', uri)
                data['info'] = ("Connection to database was successful", 
                                "You have to restart SeisHub in order to " + \
                                "see any changes at the database settings.")
            self.config.save()
        data['verbose'] = self.config.getbool('db', 'verbose')
        data['pool_size'] = self.config.getint('pool_size', 'pool_size')
        data['max_overflow'] = self.config.getint('max_overflow', 
                                                  'max_overflow')
        return data


class DatabaseQueryPanel(Component):
    """
    Query the database via HTTP form.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'catalog_db_query.tmpl'
    panel_ids = ('catalog', 'Catalog', 'db-query', 'Query DB')
    has_roles = ['CATALOG_ADMIN']
    
    def render(self, request):
        db = self.env.db.engine
        tables = sorted(db.table_names())
        data = {
            'query': 'select 1 LIMIT 20;', 
            'result': '',
            'cols': '',
            'tables': tables,
            'views': self.env.db.getViews(),
            'prefix': DEFAULT_PREFIX,
        }
        args = request.args
        if request.method=='POST':
            query = None
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
            elif 'table' in args.keys():
                table = DEFAULT_PREFIX + request.args['table'][0]
                query = 'SELECT * FROM ' + table + ' LIMIT 20;'
            elif 'view' in args.keys():
                view = request.args['view'][0]
                query = 'SELECT * FROM "' + view + '" LIMIT 20;'
            if query:
                data['query'] = query
                try:
                    query = db.execute(query)
                    data['cols'] = query.keys
                    data['result'] = query.fetchall()
                except Exception, e:
                    self.env.log.error('Database query error', e)
                    data['error'] = ('Database query error', e)
        return data


class ResourcesPanel(Component):
    """
    List all resources.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'catalog_resources.tmpl'
    panel_ids = ('catalog', 'Catalog', 'resources', 'Resources')
    has_roles = ['CATALOG_ADMIN']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        # remove SeisHub packages and resource types
        packages.remove('seishub')
        resourcetypes.pop('seishub')
        
        data = {
            'file': '', 
            'package_id': '',
            'resourcetype_id': '',
            'resturl': self.env.getRestUrl(),
            'packages': packages,
            'resourcetypes': resourcetypes,
        }
        if request.method=='POST':
            args = request.args
            if 'file' in args.keys():
                data['file'] = args.get('file',[''])[0]
                package_id = args.get('package_id',[''])[0]
                if package_id in packages:
                    resourcetype_id = args.get('resourcetype_id',[''])[0]
                    if resourcetype_id in resourcetypes.get(package_id, []):
                        data['package_id'] = package_id
                        data['resourcetype_id'] = resourcetype_id
                        data = self._addResource(data)
            elif 'delete' in args.keys() and 'resource[]' in args.keys():
                data['resource[]'] = args['resource[]']
                data = self._deleteResource(data)
        # fetch all URIs
        # XXX: filter (limit) or remove that later!
        temp = self.catalog.getAllResources()
        # remove all SeisHub resources
        temp = [t for t in temp if not str(t).startswith('/seishub/')]
        data['resources'] = temp 
        return data
    
    def _addResource(self, data):
        try:
            self.catalog.addResource(package_id=data['package_id'], 
                                     resourcetype_id=data['resourcetype_id'], 
                                     xml_data=data['file'])
        except InvalidParameterError, e:
            data['error'] = ("Please choose a non-empty XML document", e)
        except SeisHubError, e:
            data['error'] = ("Error adding resource", e)
        data['file']=''
        return data
    
    def _deleteResource(self, data):
        for id in data.get('resource[]',[None]):
            try:
                self.catalog.deleteResource(resource_id=id)
            except Exception, e:
                self.log.info("Error deleting resource", e)
                data['error'] = ("Error deleting resource", e)
                return data
        return data


class CatalogQueryPanel(Component):
    """
    Query the catalog via HTTP form.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'catalog_query.tmpl'
    panel_ids = ('catalog', 'Catalog', 'query', 'Query Catalog')
    has_roles = ['CATALOG_ADMIN']
    
    def render(self, request):
        data = {
            'query': '', 
            'result': '',
        }
        args = request.args
        if request.method=='POST':
            query = None
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
            if query:
                data['query'] = query
                try:
                    data['result'] = self.catalog.query(query)
                except Exception, e:
                    self.env.log.info('Catalog query error', e)
                    data['error'] = ('Catalog query error', e)
        return data
