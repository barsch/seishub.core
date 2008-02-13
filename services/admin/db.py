# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class BasicPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('db', 'Database', 'basic', 'Database Settings')
    
    def renderPanel(self, request):
        db = self.db.engine
        if request.method == 'POST':
            for option in ('database',):
                self.config.set('seishub', option, 
                                request.args.get(option,[])[0])
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
            'query': 'select 1;', 
            'result': '', 
        }
        args = request.args
        if request.method=='POST':
            if 'query' in args.keys() and 'send' in args.keys():
                query = data['query'] = request.args['query'][0]
                try:
                    data['result'] = db.execute(query).fetchall()
                except Exception, e:
                    self.env.log.error('Database query error', e)
                    data['error'] = ('Database query error', e)
        return ('db_query.tmpl', data)
