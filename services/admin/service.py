# -*- coding: utf-8 -*-

import os
import string
from twisted.web import static, http, util as webutil
from twisted.internet import threads, defer
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
        
        # process static content
        if self.path in self.static_content.keys():
            self.static_content.get(self.path).render(self)
            self.finish()
            return
        
        # redirect if only category given or web root
        if len(self.postpath)<2:
            categories = [p[0] for p in self.panel_ids]
            if self.postpath and self.postpath[0] in categories:
                # ok there is a category - redirect to first sub panel
                pages = filter(lambda p: p[0] == self.postpath[0], 
                               self.panel_ids)
                self.redirect('/'+pages[0][0]+'/'+pages[0][2])
                self.finish()
                return
            # redirect to the available panel
            self.redirect('/'+self.panel_ids[0][0]+'/'+self.panel_ids[0][2])
            self.finish()
            return
        
        # now it should be an AdminPanel
        self.cat_id = self.postpath[0]
        self.panel_id = self.postpath[1]
        
        self.panel = self.panels.get((self.cat_id, self.panel_id), None)
        if not self.panel:
            self.redirect('/'+self.panel_ids[0][0]+'/'+self.panel_ids[0][2])
            self.finish()
            return
        
        # get content in a extra thread and render after completion
        d = threads.deferToThread(self.panel.renderPanel, self) 
        d.addCallback(self._renderPanel)
        d.addErrback(self._processingFailed) 
        return
    
    def _renderPanel(self, result):
        if not result or isinstance(result, defer.Deferred):
            return
        template, data = result
        
        # no template given
        if not template:
            self.write(data)
            self.finish()
            return
        
        body = ''
        for path in self._getTemplateDirs():
            filename = path + os.sep + template
            if not os.path.isfile(filename):
                continue
            body = Template(file=filename, searchList=[data]) 
        
        # process template
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "index.tmpl"))
        temp.navigation = self._renderNavigation()
        temp.submenu = self._renderSubMenu()
        temp.version = SEISHUB_VERSION
        temp.content = body
        temp.error = self._renderError(data)
        body = str(temp)
        
        # set various default headers
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        self.setHeader('content-type', "text/html")
        self.setHeader('content-length', str(len(body)))
        
        # write content
        self.write(body)
        self.finish()
    
    def _renderError(self, data):
        """Render an error message."""
        if not data.get('error', None) and not data.get('exception', None):
            return
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "error.tmpl"))
        temp.message = data.get('error','')
        temp.exception = data.get('exception','')
        return temp
    
    def _renderNavigation(self):
        """Generate the main navigation bar."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "navigation.tmpl"))
        menuitems = [(i[0],i[1]) for i in self.panel_ids]
        menuitems = dict(menuitems).items()
        menuitems.sort()
        temp.navigation = menuitems
        temp.cat_id = self.cat_id
        return temp
    
    def _renderSubMenu(self):
        """Generate the sub menu box."""
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates"+os.sep+ \
                                               "submenu.tmpl"))
        menuitems = map((lambda p: (p[2],p[3])),
                         filter(lambda p: p[0]==self.cat_id, self.panel_ids))
        temp.submenu = menuitems
        temp.cat_id = self.cat_id
        temp.panel_id = self.panel_id
        return temp
    
    def _processingFailed(self, reason):
        self.env.log.error('Exception rendering:', reason)
        body = ("<html><head><title>web.Server Traceback (most recent call "
                "last)</title></head><body><b>web.Server Traceback (most "
                "recent call last):</b>\n\n%s\n\n</body></html>\n"
                % webutil.formatFailure(reason))
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.setHeader('content-type',"text/html")
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        return reason
    
    def _getTemplateDirs(self):
        """Returns a list of searchable template directories."""
        dirs = [resource_filename("seishub.services.admin","templates")]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]
    
    def _initAdminPanels(self):
        """Return a list of available admin panels."""
        panel_list = ExtensionPoint(IAdminPanel).extensions(self.env)
        self.panel_ids = []
        self.panels = {}
        
        for panel in panel_list:
            # skip panels without proper interfaces
            if not hasattr(panel, 'getPanelId') or \
               not hasattr(panel, 'renderPanel'):
                continue;
            options = panel.getPanelId()
            # getPanelId has exact 4 values in a tuple
            if not isinstance(options, tuple) or len(options)!=4:
                continue
            self.panels[(options[0], options[2])] = panel
            self.panel_ids.append(options)
        
        def _orderPanelIds(p1, p2):
            if p1[0] == 'general':
                if p2[0] == 'general':
                    return cmp(p1[1:], p2[1:])
                return -1
            elif p2[0] == 'general':
                if p1[0] == 'general':
                    return cmp(p1[1:], p2[1:])
                return 1
            return cmp(p1, p2)
        self.panel_ids.sort(_orderPanelIds)
    
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
        
        # add panel specific static files
        for panel in self.panels.values():
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
    port = env.config.getint('admin', 'port') or DEFAULT_ADMIN_PORT
    service = internet.TCPServer(port, AdminService(env))
    service.setName("WebAdmin")
    return service 