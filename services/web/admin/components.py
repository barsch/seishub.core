# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.processor.interfaces import IAdminPanel
from seishub.xmldb.xmlcatalog import INDEX_TYPES


class SchemasPanel(Component):
    """Lists all installed schemas."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'edit-schemas', 'Schemas')
    
    def renderPanel(self, request):
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
        return ('components_schemas.tmpl', data)
    
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
                self.registry.schemas.delete(document_id=id)
            except Exception, e:
                self.log.info("Error deleting schemas", e)
                return {'error': ("Error deleting schemas", e)}
        return {'info': "Schema has been deleted."}


class StylesheetsPanel(Component):
    """Lists all installed stylesheets."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'edit-stylesheets', 'Stylesheets')
    
    def renderPanel(self, request):
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
        return ('components_stylesheets.tmpl', data)
    
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
                self.registry.stylesheets.delete(document_id=id)
            except Exception, e:
                self.log.info("Error deleting stylesheet", e)
                return {'error': ("Error deleting stylesheet", e)}
        return {'info': "Stylesheet has been deleted."}


class BrowserPanel(Component):
    """Browse through all installed components."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'browse-components', 
                'Component Browser')
    
    def renderPanel(self, request):
        data = {'resturl': self.env.getRestUrl()}
        return ('components_browser.tmpl', data)


class IndexesPanel(Component):
    """List all indexes and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'edit-indexes', 'Indexes')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        index_types = sorted(INDEX_TYPES)
        index_types_dict = {}
        for i,v in INDEX_TYPES.iteritems():
            index_types_dict[v] = i
        
        
        data  = {
            'index_types': index_types,
            'index_types_dict': index_types_dict,
            'indexes': [],
            'error': '',
            'xpath': '',
            'options': '',
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            if 'add' in args.keys() and 'xpath' in args.keys():
                xpath = args.get('xpath',[''])[0]
                package_id = args.get('package_id',[''])[0]
                resourcetype_id = args.get('resourcetype_id',[''])[0]
                type_id = args.get('type_id',[''])[0]
                options = args.get('options',[None])[0]
                if package_id in packages:
                    if resourcetype_id in resourcetypes.get(package_id, []):
                        data.update(self._addIndex(package_id, resourcetype_id,
                                                   xpath, type_id, options))
            elif 'delete' in args.keys() and 'index[]' in args.keys():
                data.update(self._deleteIndexes(args.get('index[]',[])))
            elif 'reindex' in args.keys() and 'index[]' in args.keys():
                data.update(self._reindex(args.get('index[]',[])))
        # fetch all indexes
        data['indexes'] = self.catalog.listIndexes()
        return ('components_indexes.tmpl', data)
    
    def _reindex(self, data=[]):
        for part in data:
            try:
                _, package_id, resourcetype_id, xpath = part.split('/', 3)
                self.env.catalog.reindex(package_id=package_id, 
                                         resourcetype_id=resourcetype_id, 
                                         xpath = '/' + xpath)
            except Exception, e:
                self.log.error("Error reindexing index %s" % part, e)
                return {'error': ("Error reindexing index %s" % part, e)}
        return {'info': "Index has been updated."}
    
    def _deleteIndexes(self, data=[]):
        for part in data:
            try:
                _, package_id, resourcetype_id, xpath = part.split('/', 3)
                self.catalog.removeIndex(package_id=package_id, 
                                         resourcetype_id=resourcetype_id, 
                                         xpath = '/' + xpath)
            except Exception, e:
                self.log.error("Error removing index %s" % part, e)
                return {'error': ("Error removing index %s" % part, e)}
        return {'info': "Index has been removed."}
    
    def _addIndex(self, package_id, resourcetype_id, xpath, type_id, options):
        try:
            self.catalog.registerIndex(package_id, 
                                       resourcetype_id, 
                                       xpath, 
                                       type_id,
                                       options = options)
        except Exception, e:
            self.log.error("Error registering index", e)
            return {'error': ("Error registering index", e)}
        return {'info': "Index has been added."}


class AliasesPanel(Component):
    """List all aliases and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'edit-aliases', 'Aliases')
    
    def renderPanel(self, request):
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
        return ('components_aliases.tmpl', data)
    
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
    """Manage components."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('components', 'Components', 'quickinstaller', 
                'Quickinstaller')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        
        if request.method=='POST':
            args = request.args
            if 'rebuild' in args.keys():
                self.env.tree.update()
        
        data = {'packages': packages,
                'resourcetypes': resourcetypes,
                'tree': self.env.tree._registry }
        return ('components_quickinstaller.tmpl', data)
