# -*- coding: utf-8 -*-

import os

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub.defaults import DEFAULT_REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption


class RESTRequest(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
    
    def process(self):
        """Start processing a request."""
        # root element
        if self.path == '/':
            self.write("I am a REST server - serving atm nothing ;)")
            self.finish()
            return
        
        # process in thread
        d = threads.deferToThread(self._process)
        d.addErrback(self._processingFailed)
    
    def _process(self):
        """Identify HTTP method."""
        if self.method.upper() == 'GET':
            self._processGET()
        elif self.method.upper() == 'PUT':
            self._processPUT()
        elif self.method.upper() == 'POST':
            self._processPOST()
        elif self.method.upper() == 'DELETE':
            self._processDELETE()
        else:
            #Service does not implement handlers for this HTTP verb (e.g. HEAD) 
            #Return HTTP status code 405 (Method Not Allowed)
            self.setResponseCode(http.NOT_ALLOWED)
            self.finish()
    
    def _processGET(self):
        """
        Handles a HTTP GET request. 
        
        First we try to resolve to a unique resource directly. If a resource 
        can't be found we lookup the aliases dictionary. If it still fails, we
        use the mapping plug-ins.
        """
        # try to get resource from catalog directly
        result = self._isResource()
        if result:
            self._processResource(result)
        # test if alias 
        elif self.path in self.env.catalog.aliases:
            self._processAlias()
        # test if mapping exists
        
        else:
            self._setHeaders()
            self.setResponseCode(http.NOT_FOUND)
            self.finish()
    
    def _setHeaders(self, content=None, content_type='text/xml'):
        """Sets standard headers."""
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        if content:
            self.setHeader('content-type', content_type+"; charset=UTF-8")
            self.setHeader('content-length', str(len(str(content))))
   
    def _isResource(self):
        """Test if URL fits to a unique resource."""
        try:
            result = self.env.catalog.getResource(uri = self.path)
        except:
            return False
        return result
    
    def _processResource(self, result):
        try:
            result = result.getData()
            result = result.encode("utf-8")
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            self.finish()
            return
        # XXX: evaluate any given output option and use XSLT
        
        #write resource data as response
        self._setHeaders(result)
        self.setResponseCode(http.OK)
        self.write(result)
        self.finish()
    
    def _processAlias(self):
        """Generates a list of resources from an alias query."""
        urls = self.env.catalog.query(self.env.catalog.aliases[self.path])
        
        # XXX: here we need to look through all registered stylesheets for this 
        # resource type (linklist) and evaluate any given output option
        fh = open(resource_filename(self.__module__,
                          "xml"+os.sep+ "linklist_to_xhtml.xslt"))
        xslt = fh.read()
        fh.close()
        
        root = """<?xml version="1.0"?>
        <seishub xml:base="http:localhost:8080"
                 xmlns:xlink="http://www.w3.org/1999/xlink"
                 query="%s">
            %s
        </seishub>"""
        tmpl = """<link xlink:type="simple" xlink:href="%s">%s</link>"""
        doc = ""
        for url in urls:
            doc += tmpl % (url, url)
        result = str(root % (self.path, doc))
        
        # XXX: needs to be in util/wrapper class
        import libxslt
        import libxml2
        styledoc = libxml2.parseDoc(xslt)
        xmldoc = libxml2.parseDoc(result)
        style = libxslt.parseStylesheetDoc(styledoc)
        appl_style = style.applyStylesheet(xmldoc, None)
        result = str(appl_style)
        appl_style.freeDoc()
        style.freeStylesheet()
        xmldoc.freeDoc()
        
        self._setHeaders(result, 'text/html')
        self.setResponseCode(http.OK)
        self.write(result)
        self.finish()
    
    def _processPOST(self):
        """Handles a HTTP POST request."""
        uris = self.env.catalog.getUriList()
        #check if resource exists
        if self.path in uris:
            self.setResponseCode(http.NOT_FOUND)
            self.finish()
            return
        #update resource
        #XXX: missing
        self.setResponseCode(http.NOT_IMPLEMENTED)
        self.finish()
    
    def _processPUT(self):
        """Handles a HTTP PUT request."""
        uris = self.env.catalog.getUriList()
        #check if resource exists
        if self.path in uris:
            self.setResponseCode(http.CONFLICT)
            self.finish()
            return
        
        #get content and create a new resource using the given path
        try:
            content = self.content.read()
            res = self.env.catalog.newXmlResource(self.path, content)
            self.env.catalog.addResource(res)
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            self.finish()
            return
        self.setResponseCode(http.CREATED)
        self.finish()
    
    def _processDELETE(self):
        """Handles a HTTP DELETE request."""
        uris = self.env.catalog.getUriList()
        #check if resource exists
        if self.path not in uris:
            self.setResponseCode(http.NOT_FOUND)
            self.finish()
            return
        #delete resource
        try:
            self.env.catalog.deleteResource(self.path)
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            self.finish()
            return
        self.setResponseCode(http.OK)
        self.finish()
    
    def _processingFailed(self, reason):
        self.env.log.error(reason)
        self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        self.finish()
        return reason


class RESTHTTPChannel(http.HTTPChannel):
    """A receiver for HTTP requests."""
    requestFactory = RESTRequest
    
    def __init__(self):
        http.HTTPChannel.__init__(self)
        self.requestFactory.env = self.env


class RESTHTTPFactory(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = RESTHTTPChannel
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


class RESTService(internet.TCPServer):
    """Service for REST HTTP Server."""
    
    IntOption('rest', 'port', DEFAULT_REST_PORT, "WebAdmin port number.")
    
    def __init__(self, env):
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, port, RESTHTTPFactory(env))
        self.setName("REST")