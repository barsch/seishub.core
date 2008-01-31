# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SubmitXMLPanel(Component):
    """Submit and index a XML file to the database."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        yield ('catalog', 'XML Catalog', 'submit', 'Submit XML Resource')
    
    def renderPanel(self, request):
        data = {'text': '', 'uri': ''}
        if request.method=='POST':
            if 'text' and 'uri' in request.args.keys():
                # we have a textual submission 
                text = data['text'] = request.args['text'][0]
                print text
                uri = data['uri'] = request.args['uri'][0]
                res = self.env.catalog.newXmlResource(uri, text)
                d=self.env.catalog.addResource(res) 
                d.addCallback(self._finishAction, data)
                return d
            elif 'file' in request.args.keys():
                # we got a file upload
                data['text'] = request.args['file'][0]
        
        return ('catalog_submit.tmpl', data)
    
    
    def _finishAction(self, status, data):
        return ('catalog_submit.tmpl', data)