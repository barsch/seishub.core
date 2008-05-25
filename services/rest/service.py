# -*- coding: utf-8 -*-

import os

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads
from pkg_resources import resource_filename #@UnresolvedImport 
from lxml import etree

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption
from seishub.packages.processor import Processor, RequestError
from seishub.util.http import parseAccept, qualityOf, validMediaType


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
    
    def renderResource(self, content, base=''):
        # handle output/format conversion here
        self.setResponseCode(http.OK)
        return content
    
    def renderResourceList(self, **kwargs):
        # get pre-rendered resources list
        result = Processor.renderResourceList(self, **kwargs)
        # look into accept header
        accept_html = qualityOf('text/html','',self.accept)
        accept_xhtml = qualityOf('application/xhtml+xml','',self.accept)
        accept_xml = qualityOf('application/xml','',self.accept)
        # test if XHTML or HTML format is requested
        if (accept_html or accept_xhtml) > accept_xml:
            # return a XHTML document by using a stylesheet
            # XXX: Use stylesheet registry!!
            try:
                filename = resource_filename(self.__module__,"xml" + os.sep + 
                                             "linklist_to_xhtml.xslt")
                xslt = open(filename).read()
                xslt_doc = etree.XML(xslt)
                transform = etree.XSLT(xslt_doc)
                doc = etree.XML(result)
                result = transform(doc)
                self.setHeader('content-type', 'text/html; charset=UTF-8')
            except Exception, e:
                self.env.log.debug(e)
                raise RequestError(http.INTERNAL_SERVER_ERROR)
        else:
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


class RESTService(internet.TCPServer):
    """Service for the REST HTTP Server."""
    
    IntOption('rest', 'port', REST_PORT, "REST port number.")
    
    def __init__(self, env):
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, port, RESTServiceFactory(env))
        self.setName("REST")
        self.setServiceParent(env.app)