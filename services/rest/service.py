# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption, BoolOption
from seishub.packages.processor import Processor, RequestError
from seishub.util.http import parseAccept, validMediaType
from seishub.util.path import absPath


RESOURCELIST_ROOT = """<?xml version="1.0"?>
            
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
            if validMediaType(self.format):
                # add the valid format to the front of the list!
                self.accept = [(1.0, self.format, {}, {})] + self.accept
    
    def _processContent(self):
        try:
            content = Processor.process(self)
        except RequestError, e:
            self.response_code = int(e.message)
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
        # handle output/format conversion here
        if self.format:
            package_id = self.package_id
            resourcetype_id = self.resourcetype_id
            type = self.format
            data = self._transformContent(package_id, resourcetype_id, type, 
                                          data)
        self.setResponseCode(http.OK)
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler for the inheriting class."""
        root = RESOURCELIST_ROOT
        tmpl = RESOURCELIST_NODE
        doc = ""
        # generate a list of standard elements
        for tag in ['package', 'resourcetype', 'property', 'alias', 'mapping']:
            for uri in kwargs.get(tag,[]):
                content = absPath(uri[len(self.path):])[1:]
                doc += tmpl % (tag, uri, content, tag)
        # generate a list of resources
        for uri in kwargs.get('resource',[]):
            doc += tmpl % ('resource', uri, uri, 'resource')
        result = str(root % (self.env.getRestUrl(), doc))
        # set default content type to XML
        self.setHeader('content-type', 'application/xml; charset=UTF-8')
        # handle output/format conversion here
        if self.format:
            package_id = 'seishub'
            resourcetype_id = 'stylesheet'
            type = 'resourcelist:%s' % self.format
            result = self._transformContent(package_id, resourcetype_id, type, 
                                            result)
        # set header
        self._setHeaders(result)
        self.setResponseCode(http.OK)
        return result 
    
    def _transformContent(self, package_id, resourcetype_id, type, data):
        from lxml import etree
        from StringIO import StringIO
        reg = self.env.registry
        xslt = reg.stylesheets.get(package_id=package_id,
                                   resourcetype_id=resourcetype_id,
                                   type=type)
        if not xslt:
            return data
        xslt = StringIO(xslt[0].getResource().getDocument().data)
        xslt_doc = etree.parse(xslt)
        transform = etree.XSLT(xslt_doc)
        f = StringIO(data)
        doc = etree.parse(f)
        result_tree = transform(doc)
        data = str(result_tree)
        # content type should be included into the stylesheet 
        root = xslt_doc.getroot()
        content_type = root.xpath('.//xsl:output/@media-type', 
                                  namespaces=root.nsmap)
        if content_type and isinstance(content_type, list):
            self.setHeader('content-type', content_type[0] + '; charset=UTF-8')
        return data


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
