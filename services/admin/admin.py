# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor, defer
from twisted.web import static, resource, server as webserver
from zope.interface import implements
from Cheetah.Template import Template

class AdminService(Component):
    def __init__(self, service):
        resource.Resource.__init__(self)
        self.app = service
        # need to do this for resources at the root of the site
        self.putChild("", self)
        # add static files
        self.putChild('css', static.File("htdocs/css/"))
        self.putChild('favicon.ico', static.File("htdocs/favicon.ico"))

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