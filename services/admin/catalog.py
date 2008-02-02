# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SubmitXMLPanel(Component):
    """Submit and index a XML file to the database."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'submit', 'Submit XML Resource')
    
    def renderPanel(self, request):
        data = {
            'text': '', 
            'uri': '',
            'error': ''
        }
        if request.method=='POST':
            if 'text' and 'uri' in request.args.keys():
                # we have a textual submission
                text = data['text'] = request.args['text'][0]
                uri = data['uri'] = request.args['uri'][0]
                res = self.env.catalog.newXmlResource(uri, text)
                # XXX: Error checking!
                self.env.catalog.addResource(res)
            elif 'file' in request.args.keys():
                # we got a file upload
                data['text'] = request.args['file'][0]
        return ('catalog_submit.tmpl', data)


class ListResourcesPanel(Component):
    """List all resources."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'list', 'List Resources')
    
    def renderPanel(self, request):
        uris = self.env.catalog.getUriList()
        data  = {'uris': uris}
        return ('catalog_list.tmpl', data) 