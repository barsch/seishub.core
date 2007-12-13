# -*- coding: utf-8 -*-

from Cheetah.Template import Template

from seishub.core import Component
from seishub.services.admin.admin import AdminResource


class BasicsPanel(Component, AdminResource):
        
    def render_GET(self, request):
        output = Template(file="seishub/services/admin/tmpl/index.tmpl")
        output.navigation = Template(file="seishub/services/admin/tmpl/navigation.tmpl")
        output.main = Template(file="seishub/services/admin/tmpl/basics.tmpl")
        request.write(str(output))
        return ''
