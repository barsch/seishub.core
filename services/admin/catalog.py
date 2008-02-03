# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.defaults import DEFAULT_REST_PORT
from seishub.xmldb.xmlindex import XmlIndex


class SubmitResourcePanel(Component):
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
                data['text'] = request.args['text'][0]
                data['uri'] = request.args['uri'][0]
                res = self.env.catalog.newXmlResource(data['uri'], 
                                                      data['text'])
                # XXX: Error checking!
                try:
                    self.env.catalog.addResource(res)
                except Exception, e:
                    self.env.log.error(e)
                    data['error'] = e
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
        # XXX: REST service + Port should be saved somewhere in the environment
        port = self.env.config.getint('rest','port') or DEFAULT_REST_PORT
        data  = {
            'uris': uris,
            'resturl': 'http://localhost:' + str(port),
        }
        return ('catalog_list.tmpl', data)


class IndexesPanel(Component):
    """List all indexes and create new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'indexes', 'Indexes')
    
    def renderPanel(self, request):
        data  = {
            'indexes': [],
            'error': '',
            'key_path': '',
            'value_path': '',
        }
        if request.method=='POST':
            if 'add' and 'key_path' and 'value_path' in request.args.keys():
                data['key_path'] = request.args['key_path'][0]
                data['value_path'] = request.args['value_path'][0]
                try:
                    xml_index = XmlIndex(key_path = data['key_path'],
                                         value_path = data['value_path'])
                    self.env.catalog.registerIndex(xml_index)
                except Exception, e:
                    self.env.log.error(e)
                    data['error'] = e
        # fetch all indexes
        data['indexes'] = self.env.catalog.listIndexes()
        print data['indexes']
        return ('catalog_indexes.tmpl', data) 