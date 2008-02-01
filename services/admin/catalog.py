# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from twisted.internet import defer


class SubmitXMLPanel(Component):
    """Submit and index a XML file to the database."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        yield ('catalog', 'XML Catalog', 'submit', 'Submit XML Resource')
    
    def renderPanel(self, request):
        data = {
            'text': '', 
            'uri': '',
            'error': ''
        }
        if request.method=='POST':
            if 'text' and 'uri' in request.args.keys():
                # we have a textual submission
                data['text'] = request.args['text'][0]
                data['uri'] = request.args['uri'][0]
                return self._submitResource(data)
            elif 'file' in request.args.keys():
                # we got a file upload
                data['text'] = request.args['file'][0]
        return ('catalog_submit.tmpl', data)
    
    @defer.inlineCallbacks
    def _submitResource(self, data):
        try:
            result = yield self.env.catalog.newXmlResource(data.get('uri',''), 
                                                           data.get('text',''))
        except Exception, e:
            self.env.log.error(e)
            data['error'] = e
        try:
            result = yield self.env.catalog.addResource(result)
        except Exception, e:
            self.env.log.error(e)
            data['error'] = e
        print data
        defer.returnValue(('catalog_submit.tmpl', data))


class ListResourcesPanel(Component):
    """List all resources."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        yield ('catalog', 'XML Catalog', 'list', 'List Resources')
    
    @defer.inlineCallbacks
    def renderPanel(self, request):
        uris = yield self.env.catalog.getUriList()
        result = ('catalog_list.tmpl', {'uris': uris})
        defer.returnValue(result) 