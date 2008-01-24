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
                                               "templates/index.tmpl"))
        temp.navigation = self._getNavigation()
        temp.submenu = self._getSubMenu()
        temp.version = SEISHUB_VERSION
        content = self._getContent()
        temp.content = content.get('template','')
        self.write(str(temp))
        
        # XXX: we didn't handle status codes yet!!!!
        #if content.has_key('status'):
        self.finish()
    
    def _getContent(self):
        if not self.panel: 
            return {}
        if not hasattr(self.panel, 'renderPanel'):
            return {}
        content = self.panel.renderPanel(self, 
                                         self.panel.cat_id, 
                                         self.panel.page_id)
        if not content.has_key('template'):
            return content
        temp = ''
        for path in self._getTemplateDirs():
            filename = path + os.sep + content.get('template')
            if not os.path.isfile(filename):
                continue
            data = content.get('data',{})
            temp = Template(file=filename, searchList=[data]) 
        content['template'] = temp
        return content 
    
    def _getNavigation(self):
        """Generate the main navigation bar."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates/navigation.tmpl"))
        menuitems = self.navigation.items()
        menuitems.sort()
        temp.navigation = menuitems
        temp.cat_id = self.panel and self.panel.cat_id
        return temp
    
    def _getSubMenu(self):
        """Generate the sub menu box."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates/submenu.tmpl"))
        temp.page_id = self.panel and self.panel.page_id
        temp.cat_id = self.panel and self.panel.cat_id
        menuitems = self.submenu.get(temp.cat_id,{}).items()
        menuitems.sort()
        temp.submenu = menuitems 
        return temp
    
    def _getTemplateDirs(self):
        """Returns a list of searchable template directories."""
        print __name__
        dirs = [resource_filename("seishub.services.admin","templates")]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]
    
    def _initAdminPanels(self):
        """Returns a list of AdminPanel plug-ins."""
        self.admin_panels = ExtensionPoint(IAdminPanel).extensions(self.env)
        self.navigation = {}
        self.submenu = {}
        for panel in self.admin_panels:
            (panel.cat_id, panel.cat_name, panel.page_id, panel.page_name) = panel.getPanelId()
            self.navigation[panel.cat_id] = panel.cat_name
            if not self.submenu.has_key(panel.cat_id):
                self.submenu[panel.cat_id]={}
            self.submenu[panel.cat_id][panel.page_id] = panel.page_name
    
    
    def _initStaticContent(self):
        """Returns a dictionary of static web resources."""
        default_css = static.File(resource_filename("seishub.services.admin",
                                                    "htdocs/css/default.css"))
        default_ico = static.File(resource_filename("seishub.services.admin",
                                                    "htdocs/favicon.ico"),
                                  defaultType="image/x-icon")
        quake_gif = static.File(resource_filename("seishub.services.admin",
                                                  "htdocs/images/quake.gif"))
        # default static files
        self.static_content = {'/css/default.css': default_css,
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


class AdminHTTPFactory(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = AdminHTTP
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env
