# -*- coding: utf-8 -*-

import os
import string
import urllib

from twisted.web import static, http, util as webutil
from twisted.internet import threads, defer, ssl
from twisted.application import internet
from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import ExtensionPoint, SeisHubError
from seishub.defaults import ADMIN_PORT, ADMIN_CERTIFICATE, ADMIN_PRIVATE_KEY
from seishub.config import IntOption, Option
from seishub.packages.processor import Processor, RequestError


class AdminRequest(http.Request):
    """A HTTP request."""
    
    def __init__(self, *args, **kw):
        http.Request.__init__(self, *args, **kw)
        self._initAdminPanels()
        self._initStaticContent()
    
    def process(self):
        """
        Running through the process chain. First we look for default and user 
        defined static content. If this doesn't solve the request, we will try
        to fit in a admin panel.
        """
        # post process self.path
        self.postpath = map(urllib.unquote, string.split(self.path[1:], '/'))
        
        # process REST redirects
        if self.postpath[0]=='rest':
            return self._renderRESTContent()
        
        # process user defined static content
        if self.path in self.static_content.keys():
            return self._renderUserDefinedStatics()
        
        # process system wide default static content
        if self.postpath[0] in ['images', 'css', 'js', 'favicon.ico']:
            return self._renderDefaultStatics()
        
        # redirect if only category given or web root
        if len(self.postpath)<2:
            categories = [p[0] for p in self.panel_ids]
            if self.postpath[0] in categories:
                # ok there is a category - redirect to first sub panel
                pages = filter(lambda p: p[0] == self.postpath[0], 
                               self.panel_ids)
                menuitems = [p[2] for p in pages]
                menuitems.sort()
                self.redirect('/'+pages[0][0]+'/'+menuitems[0])
                self.finish()
                return
            # redirect to the available panel
            self.redirect('/'+self.panel_ids[0][0]+'/'+self.panel_ids[0][2])
            self.finish()
            return
        
        # now it should be an AdminPanel
        self.cat_id = self.postpath[0]
        self.panel_id = self.postpath[1]
        
        # test if panel exists
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
    
    def _renderRESTContent(self):
        """
        Sends a request to the local REST service and returns the resulting XML
        document.
        
        Asynchronous calls from JavaScript are only allowed from the same 
        server (ip and port). So in order to fetch a REST request via the admin
        service, we need to provide a REST fetcher on server side.
        """ 
        request = Processor(self.env)
        request.method = 'GET'
        request.path = self.path[5:]
        try:
            data = request.process()
        except RequestError, e:
            self.finish()
            return
        self.write(data)
        self.finish()
        self.setHeader('content-type', 'application/xml; charset=UTF-8')
        self.setResponseCode(http.OK)
        return
    
    def _renderUserDefinedStatics(self):
        """
        Render user defined static files, like CSS, JavaScript and Images.
        """ 
        filename = self.static_content.get(self.path)
        node = static.File(filename)
        node.render(self)
        self.finish()
        return
    
    def _renderDefaultStatics(self):
        """
        Render default static files, like CSS, JavaScript and Images.
        """ 
        node = static.File(resource_filename(self.__module__, 'htdocs' + 
                                             os.sep + self.postpath[0]))
        for p in self.postpath[1:]:
            node = node.getChild(p, self)
        if not node.isLeaf:
            self.setHeader('content-type', "text/html; charset=UTF-8")
        node.render(self)
        self.finish()
        return
    
    def _renderPanel(self, result):
        """
        Render the selected panel.
        """ 
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
        temp = Template(file=resource_filename(self.__module__,
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
        self.setHeader('content-type', "text/html; charset=UTF-8")
        self.setHeader('content-length', str(len(body)))
        
        # write content
        self.write(body)
        self.finish()
    
    def _renderError(self, data):
        """Render an error message."""
        if not data.get('error', None) and not data.get('exception', None):
            return
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "error.tmpl"))
        msg = data.get('error', '')
        if isinstance(msg, basestring):
            temp.message = msg
            temp.exception = None
        elif isinstance(msg, tuple) and len(msg)==2:
            temp.message = str(msg[0])
            temp.exception = str(msg[1])
        else:
            temp.message = str(msg)
            temp.exception = None
        return temp
    
    def _renderNavigation(self):
        """Generate the main navigation bar."""
        temp = Template(file=resource_filename(self.__module__,
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
        temp = Template(file=resource_filename(self.__module__,
                                               "templates"+os.sep+ \
                                               "submenu.tmpl"))
        menuitems = map((lambda p: (p[2],p[3])),
                         filter(lambda p: p[0]==self.cat_id, self.panel_ids))
        menuitems = dict(menuitems).items()
        menuitems.sort()
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
        dirs = [resource_filename(self.__module__, "templates")]
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
        self.static_content = {}
        # add panel specific static files
        for panel in self.panels.values():
            if hasattr(panel, 'getHtdocsDirs'):
                items = panel.getHtdocsDirs()
                if isinstance(items, dict):
                    self.static_content.update(items)


class AdminHTTPChannel(http.HTTPChannel):
    """A receiver for HTTP requests."""
    requestFactory = AdminRequest
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class AdminServiceFactory(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = AdminHTTPChannel
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


class AdminService(internet.SSLServer):
    """Service for WebAdmin HTTP Server."""
    IntOption('admin', 'port', ADMIN_PORT, "WebAdmin port number.")
    Option('admin', 'private_key_file', ADMIN_PRIVATE_KEY, 'Private key file.')
    Option('admin', 'certificate_file', ADMIN_CERTIFICATE, 'Certificate file.')
    Option('admin', 'secured', 'True', "Enable HTTPS connection.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('admin', 'port')
        secured = env.config.getbool('admin', 'secured')
        priv, cert = self._getCertificates()
        if secured:
            ssl_context = ssl.DefaultOpenSSLContextFactory(priv, cert)
            internet.SSLServer.__init__(self, port, AdminServiceFactory(env),\
                                        ssl_context)
        else:
            self.method = 'TCP'
            internet.SSLServer.__init__(self, port, AdminServiceFactory(env),1)
        self.setName("WebAdmin")
        self.setServiceParent(env.app)
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        priv = self.env.config.get('admin', 'private_key_file')
        cert = self.env.config.get('admin', 'certificate_file')
        if not os.path.isfile(priv):
            priv = os.path.join(self.env.config.path, 'conf', priv)
            if not os.path.isfile(priv):
                raise SeisHubError('Missing file ' + priv)
        if not os.path.isfile(cert):
            cert = os.path.join(self.env.config.path, 'conf', cert)
            if not os.path.isfile(cert):
                raise SeisHubError('Missing file ' + cert)
        return priv, cert
        