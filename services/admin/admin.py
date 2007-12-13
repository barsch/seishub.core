# -*- coding: utf-8 -*-

from twisted.web import static, resource
from Cheetah.Template import Template

class AdminResource(resource.Resource):
    def __init__(self, env):
        resource.Resource.__init__(self)
        self.env = env
        # need to do this for resources at the root of the site
        self.putChild("", self)
        # static files
        self.putChild('css', static.File("seishub/services/admin/htdocs/css"))
        self.putChild('js',  static.File('seishub/services/admin/htdocs/js'))
        self.putChild('images', 
                      static.File('seishub/services/admin/htdocs/images'))
        self.putChild('favicon.ico', 
                      static.File("seishub/services/admin/htdocs/favicon.ico",
                                  defaultType="image/x-icon"))

class AdminService(AdminResource):
    def __init__(self, env):
        AdminResource.__init__(self, env)
        # dynamic pages
        from seishub.services.admin.basics import BasicsPanel 
        from seishub.services.admin.plugins import PluginsPanel 
        from seishub.services.admin.logs import LogsPanel        
        self.putChild("basics", env[BasicsPanel])
        self.putChild("plugins", env[PluginsPanel])
        self.putChild("logs", env[LogsPanel])
        

    def render_GET(self, request):
        output = Template(file="seishub/services/admin/tmpl/index.tmpl")
        output.navigation = Template(file="seishub/services/admin/tmpl/navigation.tmpl")
        output.main = "" 
        request.write(str(output))
        return ''


