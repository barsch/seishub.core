# -*- coding: utf-8 -*-

from Cheetah.Template import Template

from seishub.core import Component
from seishub.services.admin.admin import AdminResource


class LogsPanel(Component, AdminResource):

    def render_GET(self, request):
        output = Template(file="seishub/services/admin/tmpl/index.tmpl")
        output.navigation = Template(file="seishub/services/admin/tmpl/navigation.tmpl")
        output.main = Template(file="seishub/services/admin/tmpl/logs.tmpl")
        output.main.logs = str(self.env.config.sections())
        request.write(str(output))
        
        return ''
