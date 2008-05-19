# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.xmldb.defaults import DEFAULT_PREFIX, RESOURCE_TABLE, \
                                   INDEX_TABLE, INDEX_DEF_TABLE, \
                                   URI_TABLE, QUERY_ALIASES_TABLE
from seishub.xmldb.errors import UnknownUriError, AddResourceError


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbbasic', 'Database Settings')
    
    def renderPanel(self, request):
        db = self.db.engine
        if request.method == 'POST':
            for option in ('uri', 'verbose'):
                self.config.set('db', option, 
                                request.args.get(option,[''])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'uri': self.config.get('db', 'uri'),
          'verbose': self.config.get('db', 'verbose'),
          'db': db,
        }
        return ('catalog_db_basic.tmpl', data)


class DatabaseQueryPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    tables = [RESOURCE_TABLE, URI_TABLE, INDEX_TABLE, INDEX_DEF_TABLE, \
              QUERY_ALIASES_TABLE]
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbquery', 'Query DB')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        data = {
            'query': 'select 1;', 
            'result': '',
            'tables': self.tables,
        }
        args = request.args
        if request.method=='POST':
            query = None
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
            else:
                for table in self.tables:
                    if table in args.keys():
                        query = 'SELECT * FROM '+DEFAULT_PREFIX+table+';'
            if query:
                data['query'] = query
                try:
                    data['result'] = db.execute(query).fetchall()
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
        rest_port = self.config.getint('rest', 'port')
        data = {
            'file': '', 
            'uri': '',
            'resturl': 'http://localhost:' + str(rest_port) + '/seishub',
        }
        if request.method=='POST':
            args = request.args
            if 'file' in args.keys() and 'uri' in args.keys():
                data['file'] = args['file'][0]
                data['uri'] = args['uri'][0]
                data = self._addResource(data)
            elif 'delete' in args.keys() and 'resource[]' in args.keys():
                data['resource[]'] = args['resource[]']
                data = self._deleteResources(data)
        # fetch all uris
        data['resources'] = self.catalog.getUriList()
        return ('catalog_resources.tmpl', data)
    
    def _addResource(self, data):
        try:
            res = self.catalog.newXmlResource(data['uri'], data['file'])
        except Exception, e:
            self.log.error("Error creating resource", e)
            data['error'] = ("Error creating resource", e)
            return data
        try:
            self.catalog.addResource(res)
        except AddResourceError, e:
            self.log.error("Error adding resource", e)
            data['error'] = ("Error adding resource", e)
            return data
        data['uri']=''
        data['file']=''
        return data
    
    def _deleteResources(self, data):
        for id in data.get('resource[]',[]):
            try:
                self.catalog.deleteResource(id)
            except UnknownUriError, e:
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