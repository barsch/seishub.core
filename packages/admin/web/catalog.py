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
import pprint
import time


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
            self.config.set('db', 'pool_size', pool_size)
            self.config.set('db', 'max_overflow', max_overflow)
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
        data['pool_size'] = self.config.getint('db', 'pool_size')
        data['max_overflow'] = self.config.getint('db', 'max_overflow')
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
        tables = sorted([t for t in db.table_names() if DEFAULT_PREFIX in t])
        data = {
            'query': 'select 1 LIMIT 20;', 
            'result': '',
            'cols': '',
            'rows': '',
            'clock': '',
            'tables': tables,
            'views': sorted(self.env.db.getViews()),
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
                    t1 = time.clock()
                    result = db.execute(query)
                    t2 = time.clock()
                    data['clock'] = "%0.6f" % (t2-t1)
                    data['cols'] = result.keys
                    data['rows'] = result.rowcount
                    data['result'] = result.fetchall()
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
        data['resources'] = []
        # XXX: filter (limit) or remove that later!
        for package in packages:
            for resourcetype in resourcetypes.get(package, []):
                res = self.catalog.getAllResources(package, resourcetype)
                data['resources'].extend(res)
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
                self.catalog.deleteResource(resource_id = int(id))
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
            'rows': '',
            'clock': ''
        }
        args = request.args
        if request.method=='POST':
            query = None
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
            if query:
                data['query'] = query
                try:
                    t1 = time.clock()
                    result = self.catalog.query(query)
                    t2 = time.clock()
                    data['clock'] = "%0.6f" % (t2-t1)
                    data['rows'] = len(result)-1
                    data['result'] = pprint.pformat(result, 4)
                except Exception, e:
                    self.env.log.info('Catalog query error', e)
                    data['error'] = ('Catalog query error', e)
        return data


class DatabaseStatusPanel(Component):
    """
    Shows some statistics of the database.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'catalog_status.tmpl'
    panel_ids = ('catalog', 'Catalog', 'status', 'Status')
    has_roles = ['CATALOG_ADMIN']
    
    def render(self, request):
        db = self.env.db.engine
        tables = {}
        views = {}
        for table in sorted(db.table_names()):
            if not table.startswith(DEFAULT_PREFIX):
                continue
            query = 'SELECT count(*) FROM ' + table
            try:
                query = db.execute(query)
                tables[table] = query.fetchall()[0][0]
            except:
                pass
        for view in self.env.db.getViews():
            query = 'SELECT count(*) FROM ' + view
            try:
                query = db.execute(query)
                views[view] = query.fetchall()[0][0]
            except:
                pass
        return {
            'tables': tables,
            'views': views,
        }
