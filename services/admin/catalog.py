# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.xmldb.errors import UnknownUriError, AddResourceError


class ResourcesPanel(Component):
    """List all resources."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'resources', 'Resources')
    
    def renderPanel(self, request):
        rest_port = self.config.getint('rest', 'port')
        data = {
            'file': '', 
            'uri': '',
            'resturl': 'http://localhost:' + str(rest_port),
        }
        if request.method=='POST':
            args = request.args
            if 'file' and 'uri' in args.keys():
                data['file'] = args['file'][0]
                data['uri'] = args['uri'][0]
                data = self._addResource(data)
            elif 'delete' and 'resource[]' in args.keys():
                data['resource[]'] = args['resource[]']
                data = self._deleteResources(data)
        # fetch all uris
        data['resources'] = self.catalog.getUriList()
        return ('catalog_resources.tmpl', data)
    
    def _addResource(self, data):
        try:
            res = self.catalog.newXmlResource(data['uri'], data['file'])
        except Exception, e:
            self.log.error("Error creating resource", e)
            data['error'] = ("Error creating resource", e)
            return data
        try:
            self.catalog.addResource(res)
        except AddResourceError, e:
            self.log.error("Error adding resource", e)
            data['error'] = ("Error adding resource", e)
            return data
        data['uri']=''
        data['file']=''
        return data
    
    def _deleteResources(self, data):
        for id in data.get('resource[]',[]):
            try:
                self.catalog.deleteResource(id)
            except UnknownUriError, e:
                self.log.info("Error deleting resource: %s" % id, e)
                data['error'] = ("Error deleting resource: %s" % id, e)
                return data
        return data


class IndexesPanel(Component):
    """List all indexes and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'indexes', 'Indexes')
    
    def renderPanel(self, request):
        data  = {
            'indexes': [],
            'error': '',
            'xpath': '',
        }
        if request.method=='POST':
            args = request.args
            if 'add' and 'xpath' in args.keys():
                data['xpath'] = args['xpath'][0]
                data = self._addIndex(data)
            elif 'delete' and 'index[]' in args.keys():
                data['index[]'] = args['index[]']
                data = self._deleteIndexes(data)
        # fetch all indexes
        data['indexes'] = self.catalog.listIndexes()
        return ('catalog_indexes.tmpl', data)
    
    def _deleteIndexes(self, data):
        for xpath in data.get('index[]',[]):
            try:
                self.catalog.removeIndex(xpath)
            except Exception, e:
                self.log.error("Error removing xml_index %s" % xpath, e)
                data['error'] = ("Error removing xml_index %s" % xpath, e)
                return data
        return data
    
    def _addIndex(self, data):
        try:
            xml_index = self.catalog.newXmlIndex(data['xpath'])
        except Exception, e:
            self.log.error("Error generating a xml_index", e)
            data['error'] = ("Error generating a xml_index", e)
            return data
        try:
            self.catalog.registerIndex(xml_index)
        except Exception, e:
            self.log.error("Error registering xml_index", e)
            data['error'] = ("Error registering xml_index", e)
        data['xpath'] = ''
        return data