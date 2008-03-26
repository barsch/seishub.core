# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.xmldb.defaults import DEFAULT_PREFIX, RESOURCE_TABLE, \
                                   INDEX_TABLE, INDEX_DEF_TABLE, \
                                   URI_TABLE, QUERY_ALIASES_TABLE


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('db', 'Database', 'basic', 'Database Settings')
    
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
        return ('db_basic.tmpl', data)


class QueryPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    tables = [RESOURCE_TABLE, URI_TABLE, INDEX_TABLE, INDEX_DEF_TABLE, \
              QUERY_ALIASES_TABLE]
    
    def getPanelId(self):
        return ('db', 'Database', 'query', 'Query DB')
    
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
        return ('db_query.tmpl', data)
