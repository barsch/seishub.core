# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application import internet

from seishub.defaults import DEFAULT_REST_PORT


class RESTRequestHandler(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
    
    def process(self):
        self.write("I am a REST server - serving atm nothing ;)")
        self.finish()


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
    port = env.config.getint('rest','port') or DEFAULT_REST_PORT
    service = internet.TCPServer(port, RESTService(env))
    service.setName("REST")
    return service 