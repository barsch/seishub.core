# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor, defer
from twisted.web import resource, server as webserver
from Cheetah.Template import Template


class AdminService(resource.Resource):
    def __init__(self, app):
        self.app = app

    def render_GET(self, request):
        output = Template(file="seishub/services/admin/tmpl/index.tmpl")
        output.services = service.IServiceCollection(self.app)
        request.write(str(output))
        return ''

    def render_POST(self, request):
        args = request.args
        actions = []
        if args.has_key('shutdown'):
            reactor.stop()
        
        serviceList = request.args.get('service', [])
        for srv in service.IServiceCollection(self.app):
            if srv.running and not srv.name in serviceList:
                stopping = defer.maybeDeferred(srv.stopService)
                actions.append(stopping)
            elif not srv.running and srv.name in serviceList:
                # wouldn't work if this program were using reserved ports
                # and running under an unprivileged user id
                starting = defer.maybeDeferred(srv.startService)
                actions.append(starting)
        defer.DeferredList(actions).addCallback(self._finishedActions, request)
        return webserver.NOT_DONE_YET

    def _finishedActions(self, results, request):
        request.redirect('/')
        request.finish(  )