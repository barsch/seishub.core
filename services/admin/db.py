# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.defaults import CREATES


class DBSettingPanel(Component):
    """DB configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        yield ('db', 'Database', 'basic', 'Database Settings')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            for option in ('database',):
                self.config.set('seishub', option, request.args.get(option,[])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'database': self.config.get('seishub', 'database'),
        }
        return ('db_basic.tmpl', data)


class QueryDBPanel(Component):
    """Query the database via http form."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        yield ('db', 'Database', 'query', 'Query DB')
    
    def renderPanel(self, request):
        db = self.env.db.engine
        data = {
            'error': '',
            'db': db, 
            'query': 'select 1;', 
            'result': '', 
        }
        if request.method=='POST':
            if 'query' and 'send' in request.args.keys():
                query = data['query'] = request.args['query'][0]
                data['result'] = db.execute(query).fetchall()
            elif 'create' in request.args.keys():
                for query in CREATES:
                    db.execute(query).fetchall()
        return ('db_check.tmpl', data)
