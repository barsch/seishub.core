# -*- coding: utf-8 -*-

from twisted.web import http, util as webutil
from twisted.application import internet
from twisted.internet import threads

from seishub.defaults import DEFAULT_REST_PORT
from seishub import __version__ as SEISHUB_VERSION


class RESTRequestHandler(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
    
    def process(self):
        if self.path == '/':
            self.write("I am a REST server - serving atm nothing ;)")
            self.finish()
            return
        
        # use catalog to identify resources and return valid resource
        d = threads.deferToThread(self._process)
        d.addErrback(self._processingFailed)
    
    def _process(self):
        uris = self.env.catalog.getUriList()
        if not self.path in uris:
            self.write("Could not find requested resource.")
            self.finish()
            return
        result = self.env.catalog.getResource(uri = self.path)
        result = result.getData()
        
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        self.setHeader('content-type', "text/xml")
        self.setHeader('content-length', str(len(result)))
        
        self.write(result)
        self.finish()

    def _processingFailed(self, reason):
        self.env.log.error('Exception rendering:', reason)
        body = ("<html><head><title>web.Server Traceback (most recent call "
                "last)</title></head><body><b>web.Server Traceback (most "
                "recent call last):</b>\n\n%s\n\n</body></html>\n"
                % webutil.formatFailure(reason))
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.setHeader('content-type',"text/html")
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        return reason


class RESTHTTP(http.HTTPChannel):
    """A receiver for HTTP requests."""
    requestFactory = RESTRequestHandler
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class RESTService(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = RESTHTTP
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


def getRESTService(env):
    """Service for REST HTTP Server."""
    port = env.config.getint('rest', 'port') or DEFAULT_REST_PORT
    service = internet.TCPServer(port, RESTService(env))
    service.setName("REST")
    return service 