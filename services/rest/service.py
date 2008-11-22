# -*- coding: utf-8 -*-

from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption, BoolOption
from seishub.defaults import REST_PORT
from seishub.exceptions import SeisHubError, NotAllowedError
from seishub.processor import Processor
from seishub.util.http import parseAccept, validMediaType
from seishub.util.path import addBase
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.internet import defer, threads
from twisted.python import failure
from twisted.web import http, server, util


RESOURCELIST_ROOT = """<?xml version="1.0" encoding="UTF-8"?>

<seishub xml:base="%s" xmlns:xlink="http://www.w3.org/1999/xlink">%s
</seishub>
"""

RESOURCELIST_NODE = """
  <%s category="%s" xlink:type="simple" xlink:href="%s">%s</%s>"""


class RESTRequest(Processor, http.Request):
    """A REST request via the http(s) protocol."""
    
    def __init__(self, channel, queued):
        Processor.__init__(self, self.env)
        http.Request.__init__(self, channel, queued)
        self.notifications = []
    
    def process(self):
        """Process a request."""
        
        # process request
        try:
            self.render()
        except:
            self.processingFailed(failure.Failure())
    
    def render(self):
        # set standard HTTP headers
        self.setHeader('server', 'SeisHub ' + SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        
        try:
            # call the processor
            data = self._process()
        except SeisHubError, e:
            self.setResponseCode(e.code)
            self.env.log.error(http.responses.get(e.code))
            self.write('')
            self.finish()
        
        if data == server.NOT_DONE_YET:
            return
        
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
        
        # check result
        if isinstance(data, dict):
            body = self._renderFolder(data)
        elif isinstance(data, basestring):
            body = self._renderResource(data)
        else:
            raise SeisHubError()
        
        # set additional headers
        for k, v in self.response_header.iteritems():
            self.setHeader(k, v)
        
        self.setHeader('content-length', str(len(body)))
        if self.method == "HEAD":
            self.write('')
        else:
            self.write(body)
        self.finish()

    def processingFailed(self, reason):
        body = ("<html><head><title>web.Server Traceback (most recent call last)</title></head>"
                "<body><b>web.Server Traceback (most recent call last):</b>\n\n"
                "%s\n\n</body></html>\n"
                % util.formatFailure(reason))
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.setHeader('content-type',"text/html")
        self.setHeader('content-length', str(len(body)))
        self.write(body)
        self.finish()
        return reason
    
    def _renderResource(self, data):
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
    
    def _renderFolder(self, children={}):
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
        self.setResponseCode(http.OK)
        return xml_doc 
    
    def notifyFinish(self):
        """Notify when finishing the request
        
        @return: A deferred. The deferred will be triggered when the
        request is finished -- with a C{None} value if the request
        finishes successfully or with an error if the request is stopped
        by the client.
        """
        self.notifications.append(defer.Deferred())
        return self.notifications[-1]
    
    def connectionLost(self, reason):
        for d in self.notifications:
            d.errback(reason)
        self.notifications = []
    
    def finish(self):
        http.Request.finish(self)
        for d in self.notifications:
            d.callback(None)
        self.notifications = []

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
