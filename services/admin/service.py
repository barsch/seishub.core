# -*- coding: utf-8 -*-

import os
import string
from twisted.web import static, http
from twisted.web.server import NOT_DONE_YET
from twisted.internet import threads
from twisted.application import internet
from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport 
from urllib import unquote

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import ExtensionPoint
from seishub.defaults import DEFAULT_ADMIN_PORT


class AdminRequestHandler(http.Request):
    """A HTTP request."""
    
    def __init__(self, *args, **kw):
        http.Request.__init__(self, *args, **kw)
        self._initAdminPanels()
        self._initStaticContent()
    
    def process(self):
        # post process self.path
        self.postpath = map(unquote, string.split(self.path[1:], '/'))
        
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
            if len(self.postpath)>1 and \
               panel.cat_id == self.postpath[0] and \
               panel.page_id == self.postpath[1]:
                self.panel = panel
                break
            # but keep a default panel
            if panel.cat_id == self.postpath[0] and not self.panel:
                self.panel = panel
        
        if not self.panel: 
            return ''
        if not hasattr(self.panel, 'renderPanel'):
            return ''
        self._getPanelAsThread()
    
    def render(self, body):
        if body==NOT_DONE_YET:
            return
            
        # process template
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "index.tmpl"))
        temp.navigation = self._getNavigation()
        temp.submenu = self._getSubMenu()
        temp.version = SEISHUB_VERSION
        temp.content = self._getContent(body)
        content = str(temp)
        
        # set various default headers
        self.setHeader('server', 'SeisHub '+SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        self.setHeader('content-type', "text/html")
        self.setHeader('content-length', str(len(content)))
        
        # write content
        self.write(content)
        self.finish()
    
    def _getContent(self, body):
        template, data = body
        temp = ''
        for path in self._getTemplateDirs():
            filename = path + os.sep + template
            if not os.path.isfile(filename):
                continue
            temp = Template(file=filename, searchList=[data]) 
        return temp 
    
    def _getPanelAsThread(self):
        d = threads.deferToThread(self.panel.renderPanel, self)
        d.addCallback(self.render)
        return NOT_DONE_YET
   
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


def getAdminService(env):
    """Service for WebAdmin HTTP Server."""
    port = env.config.getint('admin','port') or DEFAULT_ADMIN_PORT
    service = internet.TCPServer(port, AdminService(env))
    service.setName("WebAdmin")
    return service 