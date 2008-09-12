# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.xmldb.defaults import DEFAULT_PREFIX, DATA_TABLE, \
                                   INDEX_TABLE, INDEX_DEF_TABLE, \
                                   METADATA_TABLE, METADATA_DEF_TABLE, \
                                   RESOURCE_TABLE
from seishub.packages.defaults import SCHEMA_TABLE, STYLESHEET_TABLE, \
                                      ALIAS_TABLE, PACKAGES_TABLE, \
                                      RESOURCETYPES_TABLE
from seishub.xmldb.errors import AddResourceError
from seishub.db.dbmanager import SQLITE_WARNING 


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbbasic', 'Database Settings')
    
    def renderPanel(self, request):
        db = self.db
        data = {}
        if db.engine.name=='sqlite':
            data['info'] = ('SQLite Database enabled!',
                            SQLITE_WARNING.replace('-',''))
        if request.method == 'POST':
            for option in ('uri', 'verbose'):
                self.config.set('db', option, 
                                request.args.get(option,[''])[0])
            self.config.save()
            data['info'] = "You have to restart SeisHub in order to see " + \
                           "any changes at the database settings."
        data.update({
          'uri': self.config.get('db', 'uri'),
          'verbose': self.config.getbool('db', 'verbose'),
          'db': db,
        })
        return ('catalog_db_basic.tmpl', data)


class DatabaseQueryPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    tables = [DATA_TABLE, INDEX_TABLE, INDEX_DEF_TABLE, \
              METADATA_TABLE, METADATA_DEF_TABLE, ALIAS_TABLE, SCHEMA_TABLE, \
              STYLESHEET_TABLE, RESOURCE_TABLE, PACKAGES_TABLE, \
              RESOURCETYPES_TABLE]
    
    def getPanelId(self):
        return ('catalog', 'Catalog', 'dbquery', 'Query DB')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        data = {
            'query': 'select 1;', 
            'result': '',
            'cols': '',
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
        packages = self.env.registry.packages
        resourcetypes = dict([(p, self.env.registry.getResourceTypes(p).keys())
                              for p in packages])
        
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
        
        data['resources'] = self.catalog.getResourceList()
        return ('catalog_resources.tmpl', data)
    
    def _addResource(self, data):
        try:
            self.catalog.addResource(data['package_id'], 
                                     data['resourcetype_id'], 
                                     data['file'])
        except AddResourceError, e:
            self.log.error("Error adding resource", e)
            data['error'] = ("Error adding resource", e)
            return data
        data['file']=''
        return data
    
    def _deleteResources(self, data):
        for res in data.get('resource[]',[]):
            id = res.split('/')
            if len(id)!=4:
                continue
            try:
                self.catalog.deleteResource(id[1],id[2],id[3])
            except Exception, e:
                self.log.info("Error deleting resource: %s" % res, e)
                data['error'] = ("Error deleting resource: %s" % res, e)
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