# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.exceptions import SeisHubError
from seishub.config import IntOption, BoolOption
from seishub.packages.processor import Processor
from seishub.util.http import parseAccept, validMediaType
from seishub.util.path import absPath


RESOURCELIST_ROOT = """<?xml version="1.0" encoding="UTF-8"?>
            
    <seishub xml:base="%s" xmlns:xlink="http://www.w3.org/1999/xlink">
    %s
    </seishub>"""

RESOURCELIST_NODE = """<%s xlink:type="simple" xlink:href="%s">%s</%s>\n"""


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
        self.format = ''
        if 'format' in self.args.keys():
            self.format = self.args.get('format')[0]
        if 'output' in self.args.keys():
            self.format = self.args.get('output')[0]
        if self.format and validMediaType(self.format):
            # add the valid format to the front of the list!
            self.accept = [(1.0, self.format, {}, {})] + self.accept
    
    def _processContent(self):
        try:
            content = Processor.process(self)
        except SeisHubError, e:
            self.response_code = e.code
            content = ''
            self.env.log.error(http.responses.get(self.response_code))
        content=str(content)
        self._setHeaders(content)
        self.write(content)
        self.finish()
    
    def _setHeaders(self, content=None):
        """Sets standard HTTP headers."""
        self.setHeader('server', 'SeisHub ' + SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        # content length
        if content:
            self.setHeader('content-length', str(len(str(content))))
        # set response code
        self.setResponseCode(int(self.response_code))
        # set additional headers
        for k, v in self.response_header.iteritems():
            self.setHeader(k, v)
    
    def _processingFailed(self, reason):
        self.env.log.error(reason)
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.finish()
        return reason
    
    def renderResource(self, data):
        # XXX: handle output/format conversion here
        #if self.format:
            # XXX: how to fetch that???
            #package_id = self.package_id
            #resourcetype_id = self.resourcetype_id
            #label = self.format
            #data = self._transformContent(package_id, resourcetype_id, label, 
            #                              data)
        self.setResponseCode(http.OK)
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler for the inheriting class."""
        doc = ''
        # generate a list of standard elements
        for tag in ['package', 'resourcetype', 'property', 'alias', 'mapping',
                    'folder']:
            for uri in kwargs.get(tag, []):
                content = absPath(uri[len(self.path):])[1:]
                doc += RESOURCELIST_NODE % (tag, uri, content, tag)
        # generate a list of resources
        for uri in kwargs.get('resource',[]):
            doc += RESOURCELIST_NODE % ('resource', uri, uri, 'resource')
        result = str(RESOURCELIST_ROOT % (self.env.getRestUrl(), doc))
        # set default content type to XML
        self.setHeader('content-type', 'application/xml; charset=UTF-8')
        # handle output/format conversion
        if self.format:
            reg = self.env.registry
            # fetch a xslt document object
            xslt = reg.stylesheets.get(package_id='seishub',
                                       resourcetype_id='stylesheet',
                                       type='resourcelist.%s' % self.format)
            if len(xslt):
                xslt = xslt[0]
                result = xslt.transform(result)
                if xslt.content_type:
                    self.setHeader('content-type', 
                                   xslt.content_type + '; charset=UTF-8')
        # set header
        self._setHeaders(result)
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
    BoolOption('rest', 'autostart', 'True', "Enable service on start-up.")
    IntOption('rest', 'port', REST_PORT, "REST port number.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, #@UndefinedVariable
                                    port, RESTServiceFactory(env))
        self.setName("REST")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('rest', 'autostart'):
            internet.TCPServer.privilegedStartService(self) #@UndefinedVariable
    
    def startService(self):
        if self.env.config.getbool('rest', 'autostart'):
            internet.TCPServer.startService(self) #@UndefinedVariable
