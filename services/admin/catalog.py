# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.defaults import DEFAULT_REST_PORT
from seishub.xmldb.xmlindex import XmlIndex


class ResourcesPanel(Component):
    """List all resources."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('catalog', 'XML Catalog', 'resources', 'Resources')
    
    def renderPanel(self, request):
        # XXX: REST service + Port should be saved somewhere in the environment
        port = self.env.config.getint('rest','port') or DEFAULT_REST_PORT
        data = {
            'file': '', 
            'uri': '',
            'resturl': 'http://localhost:' + str(port),
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
        data['resources'] = self.env.catalog.getUriList()
        return ('catalog_resources.tmpl', data)
    
    def _addResource(self, data):
        try:
            res = self.env.catalog.newXmlResource(data['uri'], data['file'])
        except Exception, e:
            self.env.log.error("Error creating resource", e)
            data['error'] = "Error creating resource"
            data['exception'] = e
            return data
        try:
            self.env.catalog.addResource(res)
        except Exception, e:
            self.env.log.error("Error adding resource", e)
            data['error'] = "Error adding resource"
            data['exception'] = e
            return data
        data['uri']=''
        data['file']=''
        return data
    
    def _deleteResources(self, data):
        for id in data.get('resource[]',[]):
            try:
                self.env.catalog.deleteResource(id)
            except Exception, e:
                self.env.log.error("Error deleting resource: %s" % id, e)
                data['error'] = "Error deleting resource: %s" % id
                data['exception'] = e
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
            'key_path': '',
            'value_path': '',
        }
        if request.method=='POST':
            args = request.args
            if 'add' and 'key_path' and 'value_path' in args.keys():
                data['key_path'] = args['key_path'][0]
                data['value_path'] = args['value_path'][0]
                data = self._addIndex(data)
            elif 'delete' and 'index[]' in args.keys():
                data['index[]'] = args['index[]']
                data = self._deleteIndexes(data)
        # fetch all indexes
        data['indexes'] = self.env.catalog.listIndexes()
        return ('catalog_indexes.tmpl', data)
    
    def _deleteIndexes(self, data):
        # XXX: deleting by id is possible of course , but the __id attribute of 
        # XmlIndex is for internal use only, it might not be there in the future
        # my idea was to access the indexes via their xpath expressions only
        # every expression is unique in the catalog (or at least it gets 
        # transformed to a unique key_path, value_path set), so an xpath   
        # expression corresponding to an XmlIndex is kind of an uri for that 
        # index
        for id in data.get('index[]',[]):
            print "INDEX NOT YET DELETED: ", id
        data['error'] = "INDEX SHOULD BE DELETED HERE BY ID"
        return data
    
    def _addIndex(self, data):
        try:
            # XXX: actually it was meant to be used like:
            # >>> xml_index = catalog.newXmlIndex(xpath_expression)
            # >>> catalog.register_index(xml_index)
            # no key_path / value_path stuff
            xml_index = XmlIndex(key_path = data['key_path'],
                                 value_path = data['value_path'])
        except Exception, e:
            self.env.log.error("Error generating a xml_index", e)
            data['error'] = "Error generating a xml_index"
            data['exception'] = e
            return data
        try:
            self.env.catalog.registerIndex(xml_index)
        except Exception, e:
            self.env.log.error("Error registering xml_index", e)
            data['error'] = "Error registering xml_index"
            data['exception'] = e
        data['key_path'] = ''
        data['value_path'] = ''
        return data