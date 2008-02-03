# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('db', 'Database', 'basic', 'Database Settings')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        if request.method == 'POST':
            for option in ('database',):
                self.config.set('seishub', option, request.args.get(option,[])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'database': self.config.get('seishub', 'database'),
          'db': db,
        }
        return ('db_basic.tmpl', data)


class QueryPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('db', 'Database', 'query', 'Query DB')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        data = {
            'error': '',
            'query': 'select 1;', 
            'result': '', 
        }
        if request.method=='POST':
            if 'query' and 'send' in request.args.keys():
                query = data['query'] = request.args['query'][0]
                try:
                    data['result'] = db.execute(query).fetchall()
                except Exception, e:
                    self.env.log.error(e)
                    data['error'] = e
        return ('db_query.tmpl', data)
