# -*- coding: utf-8 -*-

import string
from twisted.internet import defer

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
        cp = self.env.db.connection_pool
        data = {
            'error': '',
            'running': cp.running, 
            'query': 'select 1;', 
            'result': '', 
            'connections': cp.connections,
            'dbargs': cp.connkw,
        }
        if request.method=='POST':
            if 'query' and 'send' in request.args.keys():
                data['query'] = request.args['query'][0]
                return self._callDB(cp, data)
            elif 'create' in request.args.keys():
                data['query'] = string.join(CREATES,';\n')+';'
                return self._createDB(cp, data)
        return ('db_check.tmpl', data)
    
    @defer.inlineCallbacks
    def _callDB(self, cp, data):
        try:
            data['result'] = yield cp.runQuery(data.get('query',''))
        except Exception, e:
            self.env.log.error(e)
            data['error'] = e
        defer.returnValue(('db_check.tmpl', data))
    
    @defer.inlineCallbacks
    def _createDB(self, cp, data):
        try:
            for c in CREATES:
                print c;
                data['result'] = yield cp.runQuery(c+';')
        except Exception, e:
            self.env.log.error(e)
            data['error'] = e
        defer.returnValue(('db_check.tmpl', data))
