# -*- coding: utf-8 -*-

import os

from twisted.web import http, static
from Cheetah.Template import Template
from pkg_resources import resource_filename

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import ExtensionPoint


class AdminRequestHandler(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
        self._initAdminPanels()
        self._initStaticContent()
    
    def process(self):
        # handle web root
        if self.path=='/':
            # in category admin should be always something enabled
            self.redirect('/admin')
            self.finish()
            return
        
        # process static content first
        if self.path in self.static_content.keys():
            self.static_content.get(self.path).render(self)
            self.finish()
            return
        
        # now its maybe an AdminPanel
        self.panel = None
        for panel in self.admin_panels:
            # get the specific AdminPanel
            if '/'+panel.cat_id+'/'+panel.page_id == self.path:
                self.panel = panel
                break
            # but keep a default panel
            if '/'+panel.cat_id == self.path and not self.panel:
                self.panel = panel
        
        # render panel
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "index.tmpl"))
        temp.navigation = self._getNavigation()
        temp.submenu = self._getSubMenu()
        temp.version = SEISHUB_VERSION
        temp.content = self._getContent()
        self.write(str(temp))
        self.finish()
    
    def _getContent(self):
        if not self.panel: 
            return ''
        if not hasattr(self.panel, 'renderPanel'):
            return ''
        template, data = self.panel.renderPanel(self)
        temp = ''
        for path in self._getTemplateDirs():
            filename = path + os.sep + template
            if not os.path.isfile(filename):
                continue
            temp = Template(file=filename, searchList=[data]) 
        return temp 
    
    def _getNavigation(self):
        """Generate the main navigation bar."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "navigation.tmpl"))
        menuitems = self.navigation.items()
        menuitems.sort()
        temp.navigation = menuitems
        temp.cat_id = self.panel and self.panel.cat_id
        return temp
    
    def _getSubMenu(self):
        """Generate the sub menu box."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "submenu.tmpl"))
        temp.page_id = self.panel and self.panel.page_id
        temp.cat_id = self.panel and self.panel.cat_id
        menuitems = self.submenu.get(temp.cat_id,{}).items()
        menuitems.sort()
        temp.submenu = menuitems 
        return temp
    
    def _getTemplateDirs(self):
        """Returns a list of searchable template directories."""
        dirs = [resource_filename("seishub.services.admin","templates")]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]
    
    def _initAdminPanels(self):
        """Returns a list of AdminPanel plug-ins."""
        # XXX: Performance ??
        self.admin_panels = ExtensionPoint(IAdminPanel).extensions(self.env)
        self.navigation = {}
        self.submenu = {}
        for p in self.admin_panels:
            (p.cat_id, p.cat_name, p.page_id, p.page_name) = p.getPanelId()
            self.navigation[p.cat_id] = p.cat_name
            if not self.submenu.has_key(p.cat_id):
                self.submenu[p.cat_id]={}
            self.submenu[p.cat_id][p.page_id] = p.page_name
    
    
    def _initStaticContent(self):
        """Returns a dictionary of static web resources."""
        default_css = static.File(resource_filename("seishub.services.admin",
                                                    "htdocs"+os.sep+"css"+ \
                                                    os.sep+"default.css"))
        default_ico = static.File(resource_filename("seishub.services.admin",
                                                    "htdocs"+os.sep+\
                                                    "favicon.ico"),
                                  defaultType="image/x-icon")
        default_js = static.File(resource_filename("seishub.services.admin",
                                                   "htdocs"+os.sep+"js"+ \
                                                   os.sep+"default.js"))
        quake_gif = static.File(resource_filename("seishub.services.admin",
                                                  "htdocs"+os.sep+"images"+ \
                                                  os.sep+"quake.gif"))
        # default static files
        self.static_content = {'/css/default.css': default_css,
                               '/js/default.js': default_js,
                               '/favicon.ico': default_ico,
                               '/images/quake.gif': quake_gif,}
        
        # panel specific static files
        for panel in self.admin_panels:
            if hasattr(panel, 'getHtdocsDirs'):
                items = panel.getHtdocsDirs()
                for path, child in items:
                    self.static_content[path] = static.File(child)


class AdminHTTP(http.HTTPChannel):
    """A receiver for HTTP requests."""
    requestFactory = AdminRequestHandler
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class AdminService(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = AdminHTTP
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env
