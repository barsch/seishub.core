# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SchemasPanel(Component):
    """Lists all installed schemas."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'schemas', 'Schemas')
    
    def renderPanel(self, request):
        data = {}
        return ('package_schemas.tmpl', data)


class StylesheetsPanel(Component):
    """Lists all installed stylesheets."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'stylesheets', 'Stylesheets')
    
    def renderPanel(self, request):
        data = {}
        return ('package_stylesheets.tmpl', data)


class ListPackagesPanel(Component):
    """Lists all installed packages."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'packages', 'Packages')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = dict([(p, self.env.registry.getResourceTypes(p).keys())
                              for p in packages])
        
        data = {}
        data['packages'] = packages
        data['resourcetypes'] = resourcetypes
        data['resturl'] = self.env.getRestUrl()
        return ('package_list.tmpl', data)


class IndexesPanel(Component):
    """List all indexes and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'indexes', 'Indexes')
    
    def renderPanel(self, request):
        data  = {
            'indexes': [],
            'error': '',
            'xpath': '',
        }
        if request.method=='POST':
            args = request.args
            if 'add' in args.keys() and 'xpath' in args.keys():
                data['xpath'] = args['xpath'][0]
                data = self._addIndex(data)
            elif 'delete' in args.keys() and 'index[]' in args.keys():
                data['index[]'] = args['index[]']
                data = self._deleteIndexes(data)
            elif 'reindex' in args.keys() and 'index[]' in args.keys():
                data['index[]'] = args['index[]']
                data = self._reindex(data)
        # fetch all indexes
        data['indexes'] = self.catalog.listIndexes()
        return ('package_indexes.tmpl', data)
    
    def _reindex(self, data):
        for xpath in data.get('index[]',[]):
            try:
                self.env.catalog.reindex(xpath)
            except Exception, e:
                self.log.error("Error reindexing xml_index %s" % xpath, e)
                data['error'] = ("Error reindexing xml_index %s" % xpath, e)
                return data
        return data
    
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


class AliasesPanel(Component):
    """List all aliases and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'aliases', 'Aliases')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = dict([(p, self.env.registry.getResourceTypes(p).keys())
                              for p in packages])
        
        data  = {
            'aliases': {},
            'error': '',
            'alias': '',
            'xpath': '',
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            if 'add' in args.keys() and 'xpath' in args.keys() and \
               'alias' in args.keys():
                data['alias'] = args['alias'][0]
                data['xpath'] = args['xpath'][0]
                data = self._addAlias(data)
            elif 'delete' in args.keys() and 'alias[]' in args.keys():
                data['alias[]'] = args['alias[]']
                data = self._deleteAliases(data)
        # fetch all aliases
        data['aliases'] = self.catalog.aliases
        return ('package_aliases.tmpl', data)
    
    def _deleteAliases(self, data):
        for alias in data.get('alias[]',[]):
            del self.catalog.aliases[alias]
        return data
    
    def _addAlias(self, data):
        try:
            self.catalog.aliases[data['alias']]=data['xpath']
        except Exception, e:
            self.log.error("Error generating an alias", e)
            data['error'] = ("Error generating an alias", e)
            return data
        data['alias'] = ''
        data['xpath'] = ''
        return data
