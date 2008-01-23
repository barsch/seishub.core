# -*- coding: utf-8 -*-

import os

from twisted.web import static, resource
from Cheetah.Template import Template
from pkg_resources import resource_filename

from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import Component, ExtensionPoint


class AdminPanel(resource.Resource):
    def __init__(self, admin_panels, path):
        self.admin_panels = admin_panels
        self.path = path
        self.panel = None
        
        for panel in admin_panels:
            if panel.page_id == path:
                self.panel = panel
                break
        
        resource.Resource.__init__(self)
    
    def render(self, request):
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates/index.tmpl"))
        temp.navigation = self.getNavigation(request)
        content = self.getContent(request)
        temp.content = content.get('template','')
        request.write(str(temp))
        return content.get('status','')
    
    def getContent(self, request):
        if not self.panel: 
            return {}
        if not hasattr(self.panel, 'renderPanel'):
            return {}
        content = self.panel.renderPanel(request)
        if not content.has_key('template'):
            return content
        temp = ''
        for path in self.getTemplateDirs():
            filename = path + os.sep + content.get('template')
            if not os.path.isfile(filename):
                continue
            data = content.get('data',{})
            temp = Template(file=filename, searchList=[data]) 
        content['template'] = temp
        return content 
    
    def getNavigation(self, request):
        temp = Template(file=resource_filename("seishub.services.admin",
                                               "templates/navigation.tmpl"))
        temp.navigation = self.admin_panels
        temp.selected = self.panel and self.panel.page_id
        return temp

    def getTemplateDirs(self):
        dirs = [resource_filename("seishub.services.admin","templates")]
        if hasattr(self.panel, 'getTemplateDirs'):
            dirs+=self.panel.getTemplateDirs()
        return dirs[::-1]


class AdminService(Component, resource.Resource):
    """Web administration interface."""
    admin_panels = ExtensionPoint(IAdminPanel)
    
    def __init__(self):
        resource.Resource.__init__(self)
        self.setStaticContent()
        
        for panel in self.admin_panels: 
            (panel.cat_id, panel.cat_name, panel.page_id, panel.page_name) = panel.getPanelId()
            panel.id = panel.cat_id + '/' + panel.page_id
    
    def getChild(self, path, request):
        return AdminPanel(self.admin_panels, path)
    
    def setStaticContent(self):
        # default static files
        items = [
          ('css', static.File("seishub/services/admin/htdocs/css")),
          ('js', static.File('seishub/services/admin/htdocs/js')),
          ('images', static.File('seishub/services/admin/htdocs/images')),
          ('favicon.ico', static.File("seishub/services/admin/htdocs/favicon.ico",
                                      defaultType="image/x-icon")),
        ]
        for path, child in items:
            self.putChild(path, child)
        
        # panel specific static files
        for panel in self.admin_panels:
            if hasattr(panel, 'getHtdocsDirs'):
                items = panel.getHtdocsDirs()
                for path, child in items:
                    self.putChild(path, static.File(child))
