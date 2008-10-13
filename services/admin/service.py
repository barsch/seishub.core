# -*- coding: utf-8 -*-

import os
import string
import urllib

from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport
from twisted.application import internet
from twisted.internet import threads, defer, ssl
from twisted.web import static, http, util as webutil

from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption, Option, BoolOption
from seishub.core import ExtensionPoint, SeisHubError
from seishub.defaults import ADMIN_PORT, ADMIN_CERTIFICATE, \
                             ADMIN_PRIVATE_KEY, ADMIN_MIN_PASSWORD_LENGTH
from seishub.packages.processor import Processor, ProcessorError, GET
from seishub.services.admin.interfaces import IAdminPanel, IAdminTheme, \
                                              IAdminStaticContent
from seishub.util import demjson


class AdminRequest(http.Request):
    """A HTTP request on the web-based administration interface."""
    
    def process(self):
        """Running through the process chain. First we look for default and 
        user defined static content. If this doesn't solve the request, we will
        try to fit in an admin panel."""
        # post process self.path
        self.postpath = map(urllib.unquote, string.split(self.path[1:], '/'))
        
        # process REST requests
        if self.postpath[0]=='json':
            return self._renderJSONContent()
        
        # process user defined static content
        static_content = self._getAdminStaticContent()
        if static_content.has_key(self.path):
            return self._renderStaticFile(static_content.get(self.path))
        
        # process system wide default static content
        if self.postpath[0] in ['images', 'css', 'js', 'yui', 'favicon.ico']:
            return self._renderDefaultStatics()
        
        # redirect if only category given or web root
        self._initAdminPanels()
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
    
    def _renderJSONContent(self):
        """Asynchronous calls from JavaScript are only allowed from the same 
        server (ip and port). In order to fetch a REST request via the admin
        service, we need to provide a REST fetcher on the server side.
        
        Therefore we use the package.processor.Processor directly to serve any
        resource request and return the resulting XML document.""" 
        proc = Processor(self.env)
        try:
            data = proc.run(GET, self.path[5:])
        except ProcessorError, e:
            self.env.log.info('ProcessorError:', e)
        else:
            if not isinstance(data, dict):
                self.finish()
            # created paths for resource objects
            temp = []
            for res in data.get('resource', []):
                temp.append(str(res))
            data['resource'] = temp
            # format as json
            # XXX: use json module for Python 2.6
            data = str(demjson.encode(data))
            self.write(data)
            self.setHeader('content-type', 
                           'application/json; charset=UTF-8')
            self.setResponseCode(http.OK)
        self.finish()
    
    def _renderStaticFile(self, filename):
        """Renders static files, like CSS, JavaScript and Images.""" 
        try:
            node = static.File(filename)
            node.render(self)
        except Exception, e:
            self.env.log.error('Error:', e)
        self.finish()
    
    def _renderDefaultStatics(self):
        """Render default static files, like CSS, JavaScript and Images.""" 
        try:
            res = resource_filename(__name__, os.path.join('statics', 
                                                           self.postpath[0]))
            node = static.File(res)
            for p in self.postpath[1:]:
                node = node.getChild(p, self)
            if not node.isLeaf:
                self.setHeader('content-type', 'text/html; charset=UTF-8')
            # favicon.ico needs extra content type and encoding settings
            if self.path.endswith('.ico'):
                node.type = "image/x-icon"
                node.encoding ="charset=UTF-8"
            node.render(self)
        except Exception, e:
            self.env.log.debug('Error:', e)
        self.finish()
    
    def _renderPanel(self, result):
        """Render the selected panel.""" 
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
        res = resource_filename(__name__, os.path.join('templates',
                                                       'index.tmpl'))
        temp = Template(file=res)
        # use the theme specific CSS file
        temp.css = self.getActiveAdminThemeCSS()
        temp.navigation = self._renderNavigation()
        temp.submenu = self._renderSubMenu()
        temp.version = SEISHUB_VERSION
        temp.content = body
        temp.CSS = body.getVar('CSS','')
        temp.JAVASCRIPT = body.getVar('JAVASCRIPT','')
        temp.error = self._renderError(data)
        body = str(temp)
        
        # set various default headers
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        self.setHeader('content-type', 'text/html; charset=UTF-8')
        self.setHeader('content-length', str(len(body)))
        
        # write content
        self.write(body)
        self.finish()
    
    def _renderError(self, data):
        """Render an error or info message."""
        if not data:
            return
        if data.get('error', False):
            msg = data.get('error')
            type = 'error'
        elif data.get('info', False):
            msg = data.get('info')
            type = 'info'
        else:
            return
        res = resource_filename(__name__, os.path.join('templates',
                                                       'error.tmpl'))
        temp = Template(file=res)
        temp.type = type
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
        res = resource_filename(__name__, os.path.join('templates',
                                                       'navigation.tmpl'))
        temp = Template(file=res)
        menuitems = [(i[0], i[1]) for i in self.panel_ids]
        menuitems = dict(menuitems).items()
        menuitems.sort()
        temp.navigation = menuitems
        temp.cat_id = self.cat_id
        return temp
    
    def _renderSubMenu(self):
        """Generate the sub menu box."""
        res = resource_filename(__name__, os.path.join('templates',
                                                       'submenu.tmpl'))
        temp = Template(file=res)
        menuitems = map((lambda p: (p[2], p[3])),
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
        self.setHeader('content-type', 'text/html; charset=UTF-8')
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        return reason
    
    def _getTemplateDirs(self):
        """Returns a list of searchable template directories."""
        dirs = [resource_filename(__name__, 'templates')]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]
    
    def getActiveAdminThemeCSS(self):
        """Return CSS request URL of the activated admin theme."""
        theme_id = self.env.config.get('webadmin', 'theme')
        themes = self.getAllAdminThemes()
        if themes.has_key(theme_id):
            return themes.get(theme_id).getThemeId()[1]
        else:
            return '/css/default.css'
    
    def getAllAdminThemes(self):
        """Return a list of all available admin themes."""
        theme_list = ExtensionPoint(IAdminTheme).extensions(self.env)
        themes={}
        for theme in theme_list:
            # skip theme without proper interfaces
            if not hasattr(theme, 'getThemeId'):
                continue;
            options = theme.getThemeId()
            # getThemeId has exact 2 values in a tuple
            if not isinstance(options, tuple) or len(options)!=2:
                continue
            themes[options[0]] = theme
        return themes
    
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
            # XXX: check here for permissions
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
    
    def _getAdminStaticContent(self):
        """Returns a dictionary of static web resources."""
        statics_list = ExtensionPoint(IAdminStaticContent).extensions(self.env)
        static_content = {}
        # add panel specific static files
        for comp in statics_list:
            if hasattr(comp, 'getStaticContent'):
                items = comp.getStaticContent()
                if isinstance(items, dict):
                    static_content.update(items)
        return static_content


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


class AdminService(internet.SSLServer): #@UndefinedVariable
    """Service for WebAdmin HTTP Server."""
    BoolOption('webadmin', 'autostart', 'True', "Enable service on start-up.")
    IntOption('webadmin', 'port', ADMIN_PORT, "WebAdmin port number.")
    Option('webadmin', 'private_key_file', ADMIN_PRIVATE_KEY, 
           'Private key file.')
    Option('webadmin', 'certificate_file', ADMIN_CERTIFICATE, 
           'Certificate file.')
    BoolOption('webadmin', 'secured', 'True', "Enable HTTPS connection.")
    Option('webadmin', 'theme', 'default', "WebAdmin Theme.")
    IntOption('webadmin', 'min_password_length', ADMIN_MIN_PASSWORD_LENGTH,
              'Minimal password length for secured services.')
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('webadmin', 'port')
        secured = env.config.getbool('webadmin', 'secured')
        priv, cert = self._getCertificates()
        if secured:
            ssl_context = ssl.DefaultOpenSSLContextFactory(priv, cert)
            internet.SSLServer.__init__(self, #@UndefinedVariable
                                        port, AdminServiceFactory(env),
                                        ssl_context) 
        else:
            self.method = 'TCP'
            internet.SSLServer.__init__(self, #@UndefinedVariable
                                        port, AdminServiceFactory(env), 1)
        self.setName("WebAdmin")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('webadmin', 'autostart'):
            internet.SSLServer.privilegedStartService(self) #@UndefinedVariable
    
    def startService(self):
        if self.env.config.getbool('webadmin', 'autostart'):
            internet.SSLServer.startService(self) #@UndefinedVariable
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        priv = self.env.config.get('webadmin', 'private_key_file')
        cert = self.env.config.get('webadmin', 'certificate_file')
        if not os.path.isfile(priv):
            priv = os.path.join(self.env.config.path, 'conf', priv)
            if not os.path.isfile(priv):
                raise SeisHubError('Missing file ' + priv)
        if not os.path.isfile(cert):
            cert = os.path.join(self.env.config.path, 'conf', cert)
            if not os.path.isfile(cert):
                raise SeisHubError('Missing file ' + cert)
        return priv, cert
        