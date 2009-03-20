# -*- coding: utf-8 -*-
"""
Component related administrative panels.
"""

from seishub.core import Component, implements
from seishub.packages.interfaces import IAdminPanel
from seishub.xmldb.index import INDEX_TYPES
import os


class SchemasPanel(Component):
    """
    Lists all installed schemas.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_schemas.tmpl'
    panel_ids = ('components', 'Components', 'edit-schemas', 'Schemas')
    has_roles = ['COMPONENT_SCHEMAS']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        data  = {
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
            'types': ['XMLSchema', 'RelaxNG', 'Schematron'],
        }
        if request.method=='POST':
            args = request.args
            if 'file' in args.keys():
                file = args.get('file',[''])[0]
                type = args.get('type',[''])[0]
                package_id = args.get('package_id',[''])[0]
                resourcetype_id = args.get('resourcetype_id',[''])[0]
                if type and package_id in packages:
                    if resourcetype_id in resourcetypes.get(package_id, []):
                        data.update(self._addSchema(package_id,
                                                    resourcetype_id,
                                                    type, file))
            elif 'delete' in args.keys() and 'schema[]' in args.keys():
                data.update(self._deleteSchema(args['schema[]']))
        # fetch all uris
        data['schemas'] = self.registry.schemas.get()
        return data
    
    def _addSchema(self, package_id, resourcetype_id, type, file):
        try:
            self.registry.schemas.register(package_id, resourcetype_id,
                                           type, file)
        except Exception, e:
            self.log.error("Error adding schemas", e)
            return {'error': ("Error adding schemas", e)}
        return {'info': "Schema has been added."}
    
    def _deleteSchema(self, ids=[]):
        for id in ids:
            try:
                self.registry.schemas.delete(document_id = int(id))
            except Exception, e:
                self.log.info("Error deleting schemas", e)
                return {'error': ("Error deleting schemas", e)}
        return {'info': "Schema has been deleted."}


class StylesheetsPanel(Component):
    """
    Lists all installed stylesheets.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_stylesheets.tmpl'
    panel_ids = ('components', 'Components', 'edit-stylesheets', 'Stylesheets')
    has_roles = ['COMPONENT_STYLESHEETS']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        
        data  = {
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            if 'file' in args.keys():
                file = args.get('file',[''])[0]
                type = args.get('type',[''])[0]
                package_id = args.get('package_id',[''])[0]
                resourcetype_id = args.get('resourcetype_id',[None])[0]
                if type and package_id in packages:
                    data.update(self._addStylesheet(package_id,
                                                    resourcetype_id,
                                                    type, file))
            elif 'delete' in args.keys() and 'stylesheet[]' in args.keys():
                data.update(self._deleteStylesheet(args['stylesheet[]']))
        # fetch all uris
        data['stylesheets'] = self.registry.stylesheets.get()
        return data
    
    def _addStylesheet(self, package_id, resourcetype_id, type, file):
        try:
            self.registry.stylesheets.register(package_id, resourcetype_id,
                                               type, file)
        except Exception, e:
            self.log.error("Error adding stylesheet", e)
            return {'error': ("Error adding stylesheet", e)}
        return {'info': "Stylesheet has been added."}
    
    def _deleteStylesheet(self, ids=[]):
        for id in ids:
            try:
                self.registry.stylesheets.delete(document_id = int(id))
            except Exception, e:
                self.log.info("Error deleting stylesheet", e)
                return {'error': ("Error deleting stylesheet", e)}
        return {'info': "Stylesheet has been deleted."}


class BrowserPanel(Component):
    """
    Browse through all installed components.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_browser.tmpl'
    panel_ids = ('components', 'Components', 'browse-components', 
                'Component Browser')
    
    def render(self, request):
        data = {'resturl': self.env.getRestUrl()}
        return data


class IndexesPanel(Component):
    """
    List all indexes and add new ones.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_indexes.tmpl'
    panel_ids = ('components', 'Components', 'edit-indexes', 'Indexes')
    has_roles = ['COMPONENT_INDEXES']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        index_types = sorted(INDEX_TYPES)
        index_types_dict = {}
        for i,v in INDEX_TYPES.iteritems():
            index_types_dict[v] = i
        
        data  = {
            'index_types': index_types,
            'index_types_dict': index_types_dict,
            'package_id': '',
            'resourcetype_id': '',
            'indexes': [],
            'error': '',
            'xpath': '',
            'label': '',
            'options': '',
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            data['package_id'] = args.get('package_id', [''])[0]
            data['resourcetype_id'] = args.get('resourcetype_id', [''])[0]
            if 'add' in args.keys() and 'xpath' in args:
                data['label'] = args.get('label', [''])[0]
                data['xpath'] = args.get('xpath', [''])[0]
                data['type_id'] = args.get('type_id', [''])[0]
                data['options'] = args.get('options', [None])[0]
                data = self._addIndex(data)
            elif 'delete' in args and 'index[]' in args:
                data['index[]'] = args['index[]']
                data = self._deleteIndexes(data)
            elif 'reindex' in args and 'index[]' in args:
                data['index[]'] = args['index[]']
                data = self._reindexIndexes(data)
            elif 'reindex-all' in args:
                data = self._reindexResourceType(data)
            elif 'filter' in args:
                data = self._getIndexes(data)
        return data
    
    def _getIndexes(self, data):
        # fetch all indexes
        data['indexes'] = self.catalog.getIndexes(
            package_id = data['package_id'],
            resourcetype_id = data['resourcetype_id']
        )
        return data
    
    def _reindexIndexes(self, data):
        for id in data.get('index[]', [None]):
            try:
                self.env.catalog.reindexIndex(index_id = int(id))
            except Exception, e:
                self.log.error("Error reindexing index", e)
                data['error'] = {'error': ("Error reindexing index", e)}
                break
        if not data['error']:
            data['info'] = "Indexes have been updated."
        return data
    
    def _reindexResourceType(self, data):
        try:
            self.env.catalog.reindexResourceType(
                package_id = data['package_id'],
                resourcetype_id = data['resourcetype_id']
            )
        except Exception, e:
            self.log.error("Error reindexing all resources", e)
            data['error'] = {'error': ("Error reindexing resources", e)}
        else:
            data['info'] = "Resources have been reindexed."
        return data
    
    def _deleteIndexes(self, data):
        for id in data.get('index[]', [None]):
            try:
                self.catalog.deleteIndex(index_id = int(id))
            except Exception, e:
                self.log.error("Error removing index", e)
                data['error'] = {'error': ("Error removing index", e)}
                break
        if not data['error']:
            data['info'] = "Indexes have been removed."
        return data
    
    def _addIndex(self, data):
        try:
            self.catalog.registerIndex(data['package_id'], 
                                       data['resourcetype_id'], 
                                       data['label'], 
                                       data['xpath'], 
                                       data['type_id'],
                                       options = data['options'])
        except Exception, e:
            self.log.error("Error adding index", e)
            data['error'] = ("Error adding index", e)
        else:
            data['info'] = "Index has been added."
        return data


class AliasesPanel(Component):
    """
    List all aliases and add new ones.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_aliases.tmpl'
    panel_ids = ('components', 'Components', 'edit-aliases', 'Aliases')
    has_roles = ['COMPONENT_ALIASES']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        
        data  = {
            'aliases': {},
            'error': '',
            'alias': '',
            'xpath': '',
            'sql': '',
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            package_id = args.get('package_id',[''])[0]
            resourcetype_id = args.get('resourcetype_id',[''])[0]
            alias = args.get('alias',[''])[0]
            xpath = args.get('xpath',[''])[0]
            if 'add' in args.keys() and xpath and alias:
                data.update(self._addAlias(package_id, resourcetype_id, 
                                           alias, xpath))
            elif 'delete' in args.keys() and 'alias[]' in args.keys():
                data.update(self._deleteAliases(args.get('alias[]',[])))
        # fetch all aliases
        data['aliases'] = self.env.registry.aliases
        return data
    
    def _deleteAliases(self, aliases=[]):
        for alias in aliases:
            try:
                self.env.registry.aliases.delete(uri = alias)
            except Exception, e:
                self.log.error("Error deleting an alias", e)
                return {'error': ("Error deleting an alias", e)}
        return {'info': "Alias has been deleted."}
    
    def _addAlias(self, package_id, resourcetype_id, alias, xpath):
        try:
            self.env.registry.aliases.register(package_id, 
                                               resourcetype_id, 
                                               alias, 
                                               xpath)
        except Exception, e:
            self.log.error("Error generating an alias", e)
            return {'error': ("Error generating an alias", e)}
        return {'info': "Alias has been added."}


class QuickinstallerPanel(Component):
    """
    Manage components.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'components_quickinstaller.tmpl'
    panel_ids = ('components', 'Components', 'quickinstaller', 
                 'Quickinstaller')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        
        if request.method=='POST':
            args = request.args
            if 'rebuild' in args.keys():
                self.env.update()
        
        data = {'packages': packages,
                'resourcetypes': resourcetypes,
                'tree': self.env.tree._registry }
        return data
