# -*- coding: utf-8 -*-
"""
Administrative resources.
"""

from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport
from seishub import __version__ as SEISHUB_VERSION
from seishub.core import ExtensionPoint
from seishub.processor.interfaces import IAdminPanel, IAdminTheme
from seishub.processor.resources.resource import Resource, StaticFolder
from seishub.processor.resources.filesystem import FileSystemResource
import os


class AdminPanel(Resource):
    """
    A administrative panel.
    """
    def __init__(self, root, panel):
        Resource.__init__(self)
        self.is_leaf = True
        self.category = 'admin'
        self.folderish = False
        self.panel = panel
        self.panel.root = root
        self.root = root
        self.cid, _, self.pid, _ = self.panel.panel_ids
    
    def render(self, request):
        # main page
        file = os.path.join(self.root.template_dir, 'index.tmpl')
        page = Template(file=file)
        # menus
        page.navigation = self._renderNavigation()
        page.submenu = self._renderSubMenu()
        # content
        data = self.panel.render(request)
        filename = resource_filename(self.panel.__module__, 
                                     self.panel.template)
        content = Template(file=filename, searchList=[data])
        page.content = content
        # theme specific CSS file
        page.css = self.root.getActiveAdminThemeCSS()
        # additional stuff
        page.version = SEISHUB_VERSION
        page.CSS = content.getVar('CSS','')
        page.JAVASCRIPT = content.getVar('JAVASCRIPT','')
        # error handling
        page.error = self._renderError(data)
        # default headers
        request.setHeader('content-type', 'text/html; charset=UTF-8')
        return str(page)
    
    def _renderError(self, data):
        """
        Render an error or info message.
        """
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
        file = os.path.join(self.root.template_dir, 'error.tmpl')
        temp = Template(file=file)
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
        """
        Generate the main navigation bar.
        """
        file = os.path.join(self.root.template_dir, 'navigation.tmpl')
        temp = Template(file=file)
        temp.navigation = sorted(self.root.mainmenu.items())
        temp.cat_id = self.cid
        temp.resturl = self.panel.env.getRestUrl()
        return temp
    
    def _renderSubMenu(self):
        """
        Generate the sub menu box.
        """
        file = os.path.join(self.root.template_dir, 'submenu.tmpl')
        temp = Template(file=file)
        temp.submenu = sorted(self.root.submenu[self.cid].items())
        temp.cat_id = self.cid
        temp.panel_id = self.pid
        return temp


class AdminFolder(StaticFolder):
    """
    A administrative sub folder.
    """
    def __init__(self, root, panels):
        Resource.__init__(self)
        self.category = 'admin'
        self.root = root
        self.panels = panels
        # get all admin sub panels
        for panel in panels:
            # create child
            id = panel.panel_ids[2]
            self.putChild(id, AdminPanel(root, panel))
        # set default page
        cid = panels[0].panel_ids[0]
        pid = sorted(root.submenu[cid])[0]
        self.default_page = '/admin/' + cid + '/' + pid
    
    def render_GET(self, request):
        request.redirect(self.default_page)
        return ""


class AdminRootFolder(StaticFolder):
    """
    The root folder resource containing all active administrative resources.
    """
    def __init__(self, env):
        Resource.__init__(self)
        self.env = env
        self.category = 'admin'
        # default template dir
        self.template_dir = os.path.join(self.env.config.path, 
                                         'seishub', 'services', 'web', 
                                         'admin', 'templates')
        # default template dir
        self.statics_dir = os.path.join(self.env.config.path, 
                                         'seishub', 'services', 'web', 
                                         'admin', 'statics')
        # register themes, panels and static content
        self._registerAdminThemes()
        self._registerAdminPanels()
        self._registerDefaultStaticContent()
        # set default page
        cid = sorted(self.mainmenu)[0]
        pid = sorted(self.submenu[cid])[0]
        self.default_page = '/admin/' + cid + '/' + pid
    
    def render_GET(self, request):
        request.redirect(self.default_page)
        return ""
    
    def _registerAdminThemes(self):
        """
        Register all administrative themes.
        """
        self.themes={}
        for theme in ExtensionPoint(IAdminTheme).extensions(self.env):
            # sanity checks
            if not hasattr(theme, 'theme_id'):
                msg = 'Attribute theme_id missing in %s' % theme
                self.env.log.warn(msg)
                continue
            if not hasattr(theme, 'theme_css_resource'):
                msg = 'Attribute theme_css_resource missing in %s' % theme
                self.env.log.warn(msg)
                continue
            self.themes[theme.theme_id] = theme
    
    def _registerAdminPanels(self):
        """
        Register all administrative panels.
        """
        temp = {}
        self.mainmenu={}
        self.submenu={}
        for panel in ExtensionPoint(IAdminPanel).extensions(self.env):
            # sanity checks
            if not hasattr(panel, 'panel_ids'):
                msg = 'Attribute panel_ids missing in %s' % panel
                self.env.log.warn(msg)
                continue
            if len(panel.panel_ids)!=4:
                msg = 'Attribute panel_ids got wrong format in %s' % panel
                self.env.log.warn(msg)
                continue
            if not hasattr(panel, 'template'):
                msg = 'Attribute template missing in %s' % panel
                self.env.log.warn(msg)
                continue
            if not hasattr(panel, 'render'):
                msg = 'Method render() missing in %s' % panel
                self.env.log.warn(msg)
                continue
            # create child
            cid, cname, pid, pname = panel.panel_ids
            temp.setdefault(cid, [])
            temp[cid].append(panel)
            # main menu items
            self.mainmenu[cid] = cname
            # sub menu items
            self.submenu.setdefault(cid, {})
            self.submenu[cid][pid] = pname
        for id, panels in temp.iteritems():
            self.putChild(id, AdminFolder(self, panels))
    
    def _registerDefaultStaticContent(self):
        """
        Register default static content.
        """
        for id in ['images', 'css', 'js', 'yui']:
            path = os.path.join(self.statics_dir, id)
            self.putChild(id, FileSystemResource(path))
    
    def getActiveAdminThemeCSS(self):
        """
        Return CSS request URL of the activated administrative theme.
        """
        theme_id = self.env.config.get('webadmin', 'theme')
        if self.themes.has_key(theme_id):
            return '/admin' + self.themes.get(theme_id).theme_css_resource
        else:
            return '/admin/css/magic.css'