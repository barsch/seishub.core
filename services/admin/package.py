# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class SchemasPanel(Component):
    """Lists all installed schemas."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-schemas', 'Schemas')
    
    def renderPanel(self, request):
        data = {}
        return ('package_schemas.tmpl', data)


class StylesheetsPanel(Component):
    """Lists all installed stylesheets."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-stylesheets', 'Stylesheets')
    
    def renderPanel(self, request):
        data = {}
        return ('package_stylesheets.tmpl', data)


class PackageBrowserPanel(Component):
    """Browse through all installed packages."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'browse-packages', 'Browse Packages')
    
    def renderPanel(self, request):
        packages = self.env.registry.getPackageIds()
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
        packages = self.env.registry.getPackageIds()
        resourcetypes = dict([(p, self.env.registry.getResourceTypes(p).keys())
                              for p in packages])
        
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
                data['xpath'] = args['xpath'][0]
                package_id = args.get('package',[''])[0]
                if package_id in packages:
                    resourcetype_id = args.get('resourcetype',[''])[0]
                    if resourcetype_id in resourcetypes.get(package_id, []):
                        data['package_id'] = package_id
                        data['resourcetype_id'] = resourcetype_id
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
            self.catalog.registerIndex(data['package_id'], 
                                       data['resourcetype_id'],
                                       data['xpath'])
        except Exception, e:
            self.log.error("Error registering xml_index", e)
            data['error'] = ("Error registering xml_index", e)
        data['xpath'] = ''
        return data


class AliasesPanel(Component):
    """List all aliases and add new ones."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('packages', 'Packages', 'edit-aliases', 'Aliases')
    
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
            package_id = args.get('package_id',[''])[0]
            resourcetype_id = args.get('resourcetype_id',[''])[0]
            alias = args.get('alias',[''])[0]
            xpath = args.get('xpath',[''])[0]
            if 'add' in args.keys() and xpath and alias:
                data['error'] = self._addAlias(package_id, resourcetype_id, 
                                               alias, xpath)
            elif 'delete' in args.keys() and 'alias[]' in args.keys():
                self._deleteAliases(args.get('alias[]',[])[0])
        # fetch all aliases
        data['aliases'] = self.env.registry.aliases.get()
        return ('package_aliases.tmpl', data)
    
    def _deleteAliases(self, aliases=[]):
        for alias in aliases:
            self.env.registry.aliases.delete(alias)
    
    def _addAlias(self, package_id, resourcetype_id, alias, xpath):
        try:
            self.env.registry.aliases.register(package_id, 
                                               resourcetype_id, 
                                               alias, 
                                               xpath)
        except Exception, e:
            self.log.error("Error generating an alias", e)
            return ("Error generating an alias", e)
