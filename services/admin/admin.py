# -*- coding: utf-8 -*-

from twisted.web import static, resource
from Cheetah.Template import Template

from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import Component, ExtensionPoint


class AdminPanel(resource.Resource):
    def __init__(self, admin_panels, path):
        self.admin_panels = admin_panels
        self.path = path
        self.panel = None
        for panel in admin_panels:
            if panel.id == path:
                self.panel = panel
                break
        resource.Resource.__init__(self)
    
    def render(self, request):
        temp = Template(file="seishub/services/admin/templates/index.tmpl")
        temp.navigation = self.getNavigation(request)
        temp.content, status = self.getContent(request) 
        request.write(str(temp))
        return status
    
    def getContent(self, request):
        if not self.panel:
            return '', ''
        temp = self.panel.renderPanel(request)
        template = temp.get('template','')
        data = temp.get('data','')
        status = temp.get('status','')
        if not template:
            return data, status
        return Template(file="seishub/services/admin/templates/"+template,
                        searchList=[data]), status 
    
    def getNavigation(self, request):
        temp = Template(file="seishub/services/admin/templates/navigation.tmpl")
        temp.menu = self.admin_panels
        temp.selected = self.panel and self.panel.id
        return temp


class AdminService(Component, resource.Resource):
    """Web administration interface."""
    admin_panels = ExtensionPoint(IAdminPanel)
    
    def __init__(self):
        resource.Resource.__init__(self)
        self.setStaticContent()
        # get all enabled AdminPanels
        for panel in self.admin_panels:
            temp, temp, panel.id, panel.name = panel.getPanelId()
    
    def getChild(self, path, request):
        return AdminPanel(self.admin_panels, path)
    
    def setStaticContent(self):
        # static files
        self.putChild('css', 
                      static.File("seishub/services/admin/htdocs/css"))
        self.putChild('js',  
                      static.File('seishub/services/admin/htdocs/js'))
        self.putChild('images', 
                      static.File('seishub/services/admin/htdocs/images'))
        self.putChild('favicon.ico', 
                      static.File("seishub/services/admin/htdocs/favicon.ico",
                                  defaultType="image/x-icon"))
