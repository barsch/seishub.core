# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption
from seishub.packages.processor import Processor, RequestError
from seishub.util.http import parseAccept, validMediaType


class RESTRequest(Processor, http.Request):
    """A REST request via the http(s) protocol."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
        Processor.__init__(self, self.env)
    
    def process(self):
        """Start processing a request."""
        # process headers 
        self._processHeaders()
        # process content in thread
        d = threads.deferToThread(self._processContent)
        d.addErrback(self._processingFailed)
    
    def _processHeaders(self):
        # fetch method
        self.method = self.method.upper()
        # fetch output type
        self.accept = parseAccept(self.getHeader('accept'))
        if 'format' in self.args.keys():
            format = self.args.get('format')[0]
            if validMediaType(format):
                # add the valid format to the front of the list!
                self.accept = [(1.0, format, {}, {})] + self.accept
    
    def _processContent(self):
        try:
            content = Processor.process(self)
        except RequestError, e:
            content = self._renderRequestError(int(e.message))
        content=str(content)
        self._setHeaders(content)
        self.write(content)
        self.finish()
    
    def _setHeaders(self, content=None):
        """Sets standard HTTP headers."""
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        if content:
            self.setHeader('content-length', str(len(str(content))))
    
    def _renderRequestError(self, http_status_code):
        http_status_code = int(http_status_code)
        self.setResponseCode(http_status_code)
        response_text = http.responses.get(http_status_code)
        self.env.log.error(response_text)
        return response_text
    
    def _processingFailed(self, reason):
        self.env.log.error(reason)
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.finish()
        return reason
    
    def renderResource(self, data):
        # handle output/format conversion here
        self.setResponseCode(http.OK)
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler for the inheriting class."""
        root = """<?xml version="1.0"?>
            
    <seishub xml:base="%s" xmlns:xlink="http://www.w3.org/1999/xlink">
    %s
    </seishub>"""
        tmpl = """<%s xlink:type="simple" xlink:href="%s">%s</%s>\n"""
        doc = ""
        # generate a list of standard elements
        for tag in ['package', 'resourcetype', 'property', 'alias', 'mapping',
                    'resource']:
            for uri in kwargs.get(tag,[]):
                content = uri.split('/')[-1]
                doc += tmpl % (tag, uri, content, tag)
        # XXX: xml:base doesn't work!!!!
        result = str(root % (self.env.getRestUrl(), doc))
        # set header
        self._setHeaders(result)
        self.setHeader('content-type', 'application/xml; charset=UTF-8')
        self.setResponseCode(http.OK)
        return result 


class RESTHTTPChannel(http.HTTPChannel):
    """A receiver for the HTTP requests."""
    requestFactory = RESTRequest
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class RESTServiceFactory(http.HTTPFactory):
    """Factory for the HTTP Server."""
    protocol = RESTHTTPChannel
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


class RESTService(internet.TCPServer): #@UndefinedVariable
    """Service for the REST HTTP Server."""
    
    IntOption('rest', 'port', REST_PORT, "REST port number.")
    
    def __init__(self, env):
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, #@UndefinedVariable
                                    port, RESTServiceFactory(env))
        self.setName("REST")
        self.setServiceParent(env.app)