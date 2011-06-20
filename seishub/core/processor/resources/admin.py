# -*- coding: utf-8 -*-
"""
Administrative resources.
"""

from Cheetah.Template import Template
from pkg_resources import resource_filename #@UnresolvedImport
from seishub.core import __version__ as SEISHUB_VERSION
from seishub.core.core import PackageManager
from seishub.core.packages.interfaces import IAdminPanel, IAdminTheme, \
    IAdminStaticContent
from seishub.core.processor.interfaces import IAdminResource
from seishub.core.processor.resources.filesystem import FileSystemResource
from seishub.core.processor.resources.resource import Resource, StaticFolder
from zope.interface import implements
import os


class AdminPanel(Resource):
    """
    A administrative panel.
    """
    implements(IAdminResource)

    def __init__(self, root, panel, **kwargs):
        Resource.__init__(self, **kwargs)
        self.is_leaf = True
        self.category = 'admin'
        self.folderish = False
        self.panel = panel
        self.public = self.panel.public
        self.panel.root = root
        self.root = root
        self.cid, _, self.pid, _ = self.panel.panel_ids

    def render(self, request):
        # content
        try:
            # use render() method
            data = self.panel.render(request)
        except Exception, e:
            request.env.log.error('AdminPanel rendering error', e)
            # no render() method
            data = {}
        if request.finished:
            return ""
        # stop further processing if render returns a plain string
        if not isinstance(data, dict):
            request.setHeader('content-type', 'text/plain; charset=UTF-8')
            return str(data)
        # main page
        file = os.path.join(self.root.template_dir, 'index.tmpl')
        page = Template(file=file)
        # menus
        page.navigation = self._renderNavigation()
        page.submenu = self._renderSubMenu()
        # content panel
        filename = resource_filename(self.panel.__module__,
                                     self.panel.template)
        content = Template(file=filename, searchList=[data])
        page.content = content
        # theme specific CSS file
        page.css = self.root.getActiveAdminThemeCSS()
        # additional stuff
        page.version = SEISHUB_VERSION
        page.instance = request.env.config.path
        page.CSS = content.getVar('CSS', '')
        page.JAVASCRIPT = content.getVar('JAVASCRIPT', '')
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
        temp.exception = None
        if isinstance(msg, list):
            temp.message = '<br />'.join([str(l) for l in msg])
        elif isinstance(msg, basestring):
            temp.message = msg
        elif isinstance(msg, tuple) and len(msg) == 2:
            temp.message = str(msg[0])
            temp.exception = str(msg[1])
        else:
            temp.message = str(msg)
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
    implements(IAdminResource)

    def __init__(self, root, panels, **kwargs):
        Resource.__init__(self, **kwargs)
        self.public = True
        self.category = 'admin'
        self.root = root
        self.panels = panels
        # get all admin sub panels
        for panel in panels:
            # create child
            id = panel.panel_ids[2]
            self.putChild(id, AdminPanel(root, panel))

    def render_GET(self, request):
        # set default page
        cid = self.panels[0].panel_ids[0]
        pid = sorted(self.root.submenu[cid])[0]
        default_page = '/' + '/'.join(request.prepath) + '/' + pid
        request.redirect(default_page)
        return ""


class AdminRootFolder(StaticFolder):
    """
    The root folder resource containing all active administrative resources.
    """
    implements(IAdminResource)

    def __init__(self, env, **kwargs):
        Resource.__init__(self, **kwargs)
        self.public = True
        self.env = env
        self.category = 'admin'
        # default template dir
        self.template_dir = os.path.join(self.env.getPackagePath(), 'seishub',
                                         'core', 'packages', 'admin',
                                         'web', 'templates')
        # default template dir
        self.statics_dir = os.path.join(self.env.getPackagePath(), 'seishub',
                                        'core', 'packages', 'admin',
                                        'web', 'statics')
        # register themes, panels and static content
        self._registerAdminThemes()
        self._registerAdminPanels()
        self._registerStaticContent()

    def render_GET(self, request):
        # sanity checks
        if not self.mainmenu or not self.submenu:
            return {}
        # set default page
        cid = sorted(self.mainmenu)[0]
        pid = sorted(self.submenu[cid])[0]
        default_page = '/' + '/'.join(request.prepath) + '/' + cid + '/' + pid
        request.redirect(default_page)
        return ""

    def _registerAdminThemes(self):
        """
        Register all administrative themes.
        """
        self.themes = {}
        themes = PackageManager.getComponents(IAdminTheme, None, self.env)
        for theme in themes:
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
        self.mainmenu = {}
        self.submenu = {}
        panels = PackageManager.getComponents(IAdminPanel, None, self.env)
        for panel in panels:
            # sanity checks
            if not hasattr(panel, 'panel_ids'):
                msg = 'Attribute panel_ids missing in %s' % panel
                self.env.log.warn(msg)
                continue
            if len(panel.panel_ids) != 4:
                msg = 'Attribute panel_ids got wrong format in %s' % panel
                self.env.log.warn(msg)
                continue
            if not hasattr(panel, 'template'):
                msg = 'Attribute template missing in %s' % panel
                self.env.log.warn(msg)
                continue
            if not hasattr(panel, 'render'):
                msg = 'Method render() missing in %s.' % panel
                self.env.log.info(msg)
            # set default values
            if not hasattr(panel, 'public'):
                panel.public = False
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

    def _registerStaticContent(self):
        """
        Register all static content.
        """
        # register default static content
        for id in ['images', 'css', 'js', 'yui2']:
            path = os.path.join(self.statics_dir, id)
            self.putChild(id, FileSystemResource(path, public=True))
        # favicon
        filename = os.path.join(self.statics_dir, 'favicon.ico')
        res = FileSystemResource(filename, "image/x-icon", hidden=True,
                                 public=True)
        self.putChild('favicon.ico', res)
        # start page
        filename = os.path.join(self.statics_dir, 'welcome.html')
        res = FileSystemResource(filename, "text/html; charset=UTF-8",
                                 hidden=True, public=True)
        self.putChild('welcome', res)
        # register additional static content defined by plug-ins
        static_contents = PackageManager.getComponents(IAdminStaticContent,
                                                       None, self.env)
        for res in static_contents:
            # sanity checks
            if not hasattr(res, 'getStaticContent'):
                msg = 'Method getStaticContent() missing in %s' % res
                self.env.log.warn(msg)
                continue
            items = res.getStaticContent()
            for path, file in items.iteritems():
                self.putChild(path, FileSystemResource(file, public=True))

    def getActiveAdminThemeCSS(self):
        """
        Return CSS request URL of the activated administrative theme.
        """
        theme_id = self.env.config.get('web', 'admin_theme')
        if theme_id in self.themes:
            return self.themes.get(theme_id).theme_css_resource
        else:
            return '/css/magic.css'
