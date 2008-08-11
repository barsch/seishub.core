# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SchemasPanel(Component):
    """Lists all installed schemas."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-schemas', 'Schemas')
    
    def renderPanel(self, request):
        packages = self.env.registry.packages
        resourcetypes = self.env.registry.resourcetypes
        
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
                        data['error'] = self._addSchema(package_id,
                                                        resourcetype_id,
                                                        type, file)
            elif 'delete' in args.keys() and 'schema[]' in args.keys():
                data['error'] = self._deleteSchema(args['schema[]'])
        # fetch all uris
        data['schemas'] = self.registry.schemas.get()
        return ('package_schemas.tmpl', data)
    
    def _addSchema(self, package_id, resourcetype_id, type, file):
        try:
            self.registry.schemas.register(package_id, resourcetype_id,
                                           type, file)
        except Exception, e:
            self.log.error("Error adding schemas", e)
            return ("Error adding schemas", e)
    
    def _deleteSchema(self, data=[]):
        # XXX: delete by package_id, resourcetype_id and label/type
        for uid in data:
            try:
                self.registry.schemas.delete(uid)
            except Exception, e:
                self.log.info("Error deleting schemas: %s" % uid, e)
                return ("Error deleting schemas: %s" % uid, e)


class StylesheetsPanel(Component):
    """Lists all installed stylesheets."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-stylesheets', 'Stylesheets')
    
    def renderPanel(self, request):
        packages = self.env.registry.packages
        resourcetypes = self.env.registry.resourcetypes
        
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
                        data['error'] = self._addStylesheet(package_id,
                                                            resourcetype_id,
                                                            type, file)
            elif 'delete' in args.keys() and 'stylesheet[]' in args.keys():
                data['error'] = self._deleteStylesheet(args['stylesheet[]'])
        # fetch all uris
        data['stylesheets'] = self.registry.stylesheets.get()
        return ('package_stylesheets.tmpl', data)
    
    def _addStylesheet(self, package_id, resourcetype_id, type, file):
        try:
            self.registry.stylesheets.register(package_id, resourcetype_id,
                                               type, file)
        except Exception, e:
            self.log.error("Error adding stylesheet", e)
            return ("Error adding stylesheet", e)
    
    def _deleteStylesheet(self, data=[]):
        # XXX: delete by package_id, resourcetype_id and label/type
        for uid in data:
            try:
                self.registry.stylesheets.delete(uid)
            except Exception, e:
                self.log.info("Error deleting stylesheet: %s" % uid, e)
                return ("Error deleting stylesheet: %s" % uid, e)


class PackageBrowserPanel(Component):
    """Browse through all installed packages."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'browse-packages', 'Browse Packages')
    
    def renderPanel(self, request):
        packages = self.env.registry.packages
        data = {}
        data['packages'] = packages
        data['resturl'] = self.env.getRestUrl()
        return ('package_browser.tmpl', data)


class IndexesPanel(Component):
    """List all indexes and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-indexes', 'Indexes')
    
    def renderPanel(self, request):
        packages = self.env.registry.packages
        resourcetypes = self.env.registry.resourcetypes
        
        data  = {
            'indexes': [],
            'error': '',
            'xpath': '',
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
                if package_id in packages:
                    if resourcetype_id in resourcetypes.get(package_id, []):
                        data['error'] = self._addIndex(package_id, 
                                                       resourcetype_id, 
                                                       xpath)
            elif 'delete' in args.keys() and 'index[]' in args.keys():
                data['error'] = self._deleteIndexes(args.get('index[]',[]))
            elif 'reindex' in args.keys() and 'index[]' in args.keys():
                data['error'] = self._reindex(args.get('index[]',[]))
        # fetch all indexes
        data['indexes'] = self.catalog.listIndexes()
        return ('package_indexes.tmpl', data)
    
    def _reindex(self, data=[]):
        for xpath in data:
            try:
                self.env.catalog.reindex(xpath = xpath)
            except Exception, e:
                self.log.error("Error reindexing xml_index %s" % xpath, e)
                return ("Error reindexing xml_index %s" % xpath, e)
    
    def _deleteIndexes(self, data=[]):
        for xpath in data:
            try:
                self.catalog.removeIndex(xpath = xpath)
            except Exception, e:
                self.log.error("Error removing xml_index %s" % xpath, e)
                return ("Error removing xml_index %s" % xpath, e)
    
    def _addIndex(self, package_id, resourcetype_id, xpath):
        try:
            self.catalog.registerIndex(package_id, resourcetype_id, xpath)
        except Exception, e:
            self.log.error("Error registering xml_index", e)
            return ("Error registering xml_index", e)


class AliasesPanel(Component):
    """List all aliases and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-aliases', 'Aliases')
    
    def renderPanel(self, request):
        data  = {
            'aliases': {},
            'error': '',
            'alias': '',
            'xpath': '',
            'packages': self.env.registry.packages,
            'resourcetypes': self.env.registry.resourcetypes,
            'resturl': self.env.getRestUrl(),
        }
        if request.method=='POST':
            args = request.args
            package_id = args.get('package_id',[''])[0]
            resourcetype_id = args.get('resourcetype_id',[''])[0]
            alias = args.get('alias',[''])[0]
            xpath = args.get('xpath',[''])[0]
            if 'add' in args.keys() and xpath and alias:
                data['error'] = self._addAlias(package_id, resourcetype_id, 
                                               alias, xpath)
            elif 'delete' in args.keys() and 'alias[]' in args.keys():
                data['error'] = self._deleteAliases(args.get('alias[]',[]))
        # fetch all aliases
        # XXX: ohne without .get()
        data['aliases'] = self.env.registry.aliases.get()
        return ('package_aliases.tmpl', data)
    
    def _deleteAliases(self, aliases=[]):
        for alias in aliases:
            try:
                self.env.registry.aliases.delete(uri = alias)
            except Exception, e:
                self.log.error("Error deleting an alias", e)
                return ("Error deleting an alias", e)
    
    def _addAlias(self, package_id, resourcetype_id, alias, xpath):
        try:
            self.env.registry.aliases.register(package_id, 
                                               resourcetype_id, 
                                               alias, 
                                               xpath)
        except Exception, e:
            self.log.error("Error generating an alias", e)
            return ("Error generating an alias", e)
