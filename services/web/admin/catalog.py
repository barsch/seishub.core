# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.exceptions import SeisHubError, InvalidParameterError
from seishub.processor.interfaces import IAdminPanel
from sqlalchemy import create_engine #@UnresolvedImport


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbbasic', 'Database Settings')
    
    def renderPanel(self, request):
        db = self.db
        data = {
          'db': db,
          'uri': self.config.get('db', 'uri'),
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
            verbose = request.args.get('verbose',[''])[0]
            self.config.set('db', 'verbose', verbose)
            data['uri'] = uri
            try:
                engine = create_engine(uri)
                engine.connect()
            except:
                data['error'] = ("Could not connect to database %s" % uri, 
                                 "Please make sure the database URI has " + \
                                 "the following syntax: dialect://user:" + \
                                 "password@host:port/dbname.")
            else:
                self.config.set('db', 'uri', uri)
                data['info'] = ("Connection to new database was successful", 
                                "You have to restart SeisHub in order to " + \
                                "see any changes at the database settings.")
            self.config.save()

        data['verbose'] = self.config.getbool('db', 'verbose')
        return ('catalog_db_basic.tmpl', data)


class DatabaseQueryPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbquery', 'Query DB')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        tables = sorted(db.table_names())
        data = {
            'query': 'select 1 LIMIT 20;', 
            'result': '',
            'cols': '',
            'tables': tables,
        }
        args = request.args
        if request.method=='POST':
            query = None
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
            else:
                for table in tables:
                    if table in args.keys():
                        query = 'SELECT * FROM ' + table + ' LIMIT 20;'
            if query:
                data['query'] = query
                try:
                    query = db.execute(query)
                    data['cols'] = query.keys
                    data['result'] = query.fetchall()
                except Exception, e:
                    self.env.log.error('Database query error', e)
                    data['error'] = ('Database query error', e)
        return ('catalog_db_query.tmpl', data)


class ResourcesPanel(Component):
    """List all resources."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'resources', 'Resources')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        # remove seishub from packages and resourcetypes
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
                data = self._deleteResources(data)
        # fetch all uris
        # XXX: remove that later!
        temp = self.catalog.getResourceList()
        # remove all seishub resources
        temp = [t for t in temp if not str(t).startswith('/seishub/')]
        data['resources'] = temp 
        return ('catalog_resources.tmpl', data)
    
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
    
    def _deleteResources(self, data):
        for id in data.get('resource[]',[None]):
            try:
                self.catalog.deleteResource(document_id=id)
            except Exception, e:
                self.log.info("Error deleting resource: %s" % id, e)
                data['error'] = ("Error deleting resource: %s" % id, e)
                return data
        return data


class CatalogQueryPanel(Component):
    """Query the catalog via http form."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'query', 'Query Catalog')
    
    def renderPanel(self, request):
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
        return ('catalog_query.tmpl', data)