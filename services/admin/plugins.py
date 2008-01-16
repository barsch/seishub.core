# -*- coding: utf-8 -*-

from twisted.web import server
from twisted.internet import reactor, defer
from twisted.application import service
from Cheetah.Template import Template

from seishub.core import Component
from seishub.services.admin.admin import AdminResource


class PluginsPanel(Component, AdminResource):
        
    def render_GET(self, request):
        output = Template(file="seishub/services/admin/tmpl/index.tmpl")
        output.navigation = Template(file="seishub/services/admin/tmpl/navigation.tmpl")
        output.main = Template(file="seishub/services/admin/tmpl/services.tmpl")
        output.main.services = service.IServiceCollection(self.env.app)
        request.write(str(output))
        return ''

    def render_POST(self, request):
        args = request.args
        actions = []
        if args.has_key('shutdown'):
            reactor.stop()
        
        serviceList = request.args.get('service', [])
        for srv in self.env.app.IServiceCollection(self.env.app):
            if srv.running and not srv.name in serviceList:
                stopping = defer.maybeDeferred(srv.stopService)
                actions.append(stopping)
            elif not srv.running and srv.name in serviceList:
                # wouldn't work if this program were using reserved ports
                # and running under an unprivileged user id
                starting = defer.maybeDeferred(srv.startService)
                actions.append(starting)
        defer.DeferredList(actions).addCallback(self._finishedActions, request)
        return server.NOT_DONE_YET

    def _finishedActions(self, results, request):
        request.redirect('/')
        request.finish(  )
