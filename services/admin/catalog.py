# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SubmitXMLPanel(Component):
    """Submit and index a XML file to the database."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'submit', 'Submit XML File')
    
    def renderPanel(self, request, cat_id, page_id):
        data = {'text': ''}
        if request.method=='POST':
            if 'text' in request.args.keys():
                # we have a textual submission - do something with it
                data['text'] = request.args['text'][0][::-1]
            elif 'file' in request.args.keys():
                # we got a file upload
                data['text'] = request.args['file'][0]
        print request.method
        print request.args
        
        return {'template': 'catalog_submit.tmpl', 'data': data}
