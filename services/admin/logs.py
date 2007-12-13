# -*- coding: utf-8 -*-

from twisted.web import resource

from seishub.core import Component


class LogsPanel(Component, resource.Resource):
    
    def render_GET(self, request):
        request.write("blah")
        return ''
