# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.internet import threads

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.exceptions import SeisHubError
from seishub.config import IntOption, BoolOption
from seishub.processor import Processor
from seishub.util.http import parseAccept, validMediaType
from seishub.util.path import addBase


RESOURCELIST_ROOT = """<?xml version="1.0" encoding="UTF-8"?>

<seishub xml:base="%s" xmlns:xlink="http://www.w3.org/1999/xlink">%s
</seishub>
"""

RESOURCELIST_NODE = """
  <%s category="%s" xlink:type="simple" xlink:href="%s">%s</%s>"""


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
    
    def render(self, data):
        if isinstance(data, dict):
            return self.renderFolder(data)
        else:
            return self.renderResource(data)
    
    def renderResource(self, data):
        # XXX: handle output/format conversion here
        #if self.format:
            # XXX: how to fetch that???
            #package_id = self.package_id
            #resourcetype_id = self.resourcetype_id
            #label = self.format
            #data = self._transformContent(package_id, resourcetype_id, label, 
            #                              data)
        # gzip encoding
        if not data:
            return
        encoding = self.getHeader("accept-encoding")
        if encoding and encoding.find("gzip")>=0:
            import cStringIO,gzip
            zbuf = cStringIO.StringIO()
            zfile = gzip.GzipFile(None, 'wb', 9, zbuf)
            zfile.write(data)
            zfile.close()
            self.setHeader("Content-encoding", "gzip")
            return zbuf.getvalue()
        self.setResponseCode(http.OK)
        return data
    
    def renderFolder(self, children={}):
        """Renders a folder object."""
        ids = children.keys()
        ids.sort()
        # generate a list of standard elements
        xml_doc = ''
        for id in ids:
            obj = children.get(id)
            tag = 'resource'
            category = obj.category
            if obj.folderish:
                tag = 'folder'
            uri = addBase(self.path, id)
            xml_doc += RESOURCELIST_NODE % (tag, category, uri, id, tag)
        xml_doc = str(RESOURCELIST_ROOT % (self.env.getRestUrl(), xml_doc))
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
                xml_doc = xslt.transform(xml_doc)
                if xslt.content_type:
                    self.setHeader('content-type', 
                                   xslt.content_type + '; charset=UTF-8')
        # set header
        self._setHeaders(xml_doc)
        self.setResponseCode(http.OK)
        return xml_doc 


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


class RESTService(TCPServer):
    """Service for REST HTTP server."""
    BoolOption('rest', 'autostart', 'True', "Run service on start-up.")
    IntOption('rest', 'port', REST_PORT, "REST port number.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('rest', 'port')
        TCPServer.__init__(self, port, RESTServiceFactory(env))
        self.setName("REST")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('rest', 'autostart'):
            TCPServer.privilegedStartService(self)
    
    def startService(self):
        if self.env.config.getbool('rest', 'autostart'):
            TCPServer.startService(self)
