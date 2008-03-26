# -*- coding: utf-8 -*-

import os
import string
from urllib import unquote

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub.defaults import DEFAULT_REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption
from seishub.services.rest.interfaces import IRESTProcessor
from seishub.core import ExtensionPoint


class RESTRequest(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
        self._initRESTProcessors()
    
    def process(self):
        """Start processing a request."""
        # post process self.path
        self.postpath = map(unquote, string.split(self.path[1:], '/'))
        
        # root element
        if self.path == '/':
            self.write("I am a REST server - serving atm nothing ;)")
            self.finish()
            return
        
        # process in thread
        d = threads.deferToThread(self._process)
        d.addErrback(self._processingFailed)
    
    def _process(self):
        """
        First we try to resolve to a unique resource directly. If a resource 
        can't be found we lookup the aliases dictionary. If it still fails, we
        use the mapping plug-ins.
        """
        
        self.method = self.method.upper()
        
        if self.postpath[0]=='seishub':
            if self.method=='GET':
                self._processGETResource()
            else:
                self.setResponseCode(http.NOT_ALLOWED)
                self.finish()
        elif self.method=='GET' and self.path in self.env.catalog.aliases:
            # test if alias 
            self._processAlias()
        elif self.method=='GET':
            # if not alias or not direct resource, it should be a mapping
            root_keys = self.processor_root.keys()
            root_keys.sort()
            root_keys.reverse()
            for root_key in root_keys:
                if not self.path.startswith(root_key):
                    continue
                processor_id = self.processor_root.get(root_key)
                self._processGETMapping(processor_id)
                return 
            self._setHeaders()
            self.setResponseCode(http.NOT_FOUND)
            self.finish()            
        elif self.method.upper() == 'PUT':
            self._processPUT()
        elif self.method.upper() == 'POST':
            self._processPOST()
        elif self.method.upper() == 'DELETE':
            self._processDELETE()
        else:
            self.setResponseCode(http.NOT_ALLOWED)
            self.finish()
    
    def _setHeaders(self, content=None, content_type='text/xml'):
        """Sets standard headers."""
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        if content:
            self.setHeader('content-type', content_type+"; charset=UTF-8")
            self.setHeader('content-length', str(len(str(content))))
   
    def _processGETResource(self):
        resource_id = self.path[8:]
        try:
            result = self.env.catalog.getResource(uri = resource_id)
        except Exception, e:
            self.env.log.debug(e)
            self.finish()
            return
        try:
            result = result.getData()
            result = result.encode("utf-8")
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            self.finish()
            return
        self._setHeaders(result)
        self.setResponseCode(http.OK)
        self.write(result)
        self.finish()
    
    def _processAlias(self):
        """Generates a list of resources from an alias query."""
        
        # fetch list of uris via catalog
        try:
            uris = self.env.catalog.query(self.env.catalog.aliases[self.path])
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            self.finish()
            return
        # XXX: here we need to look through all registered stylesheets for this 
        # resource type (linklist) and evaluate any given output option
        fh = open(resource_filename(self.__module__,
                          "xml"+os.sep+ "linklist_to_xhtml.xslt"))
        xslt = fh.read()
        fh.close()
        
        result = self._getResourceList(uris)
        
        if 'output' not in self.args:
            self._setHeaders(result)
            self.setResponseCode(http.OK)
            self.write(result)
            self.finish() 
        
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
    
    def _processGETMapping(self, processor_id):
        processor = self.processors.get(processor_id)
        (pid, purl, pattr) = processor.getProcessorId()
        resource_id = self.path[len(purl):]
        result = None
        if hasattr(processor, 'processGET'):
            # user handles GET processing
            result = processor.processGET(self)
            self._setHeaders(result, 'text/html')
            self.setResponseCode(http.OK)
            self.write(result)
        else:
            # automatic GET processing
            print pid,purl,pattr
            print resource_id
            print '-------'
            try:
                uris = self.env.catalog.query(resource_id)
            except Exception, e:
                self.env.log.debug(e)
                self.setResponseCode(http.NOT_FOUND)
                self.finish()
                return
            # single result
            if len(uris)==1:
                result = self._getSingleResource('/seishub' + uris[0])
            else:
                result = self._getResourceList(uris)
        if result:
            self._setHeaders(result, 'text/html')
            self.setResponseCode(http.OK)
            self.write(result)
        self.finish()
    
    def _getSingleResource(self, uri):
        try:
            result = self.env.catalog.getResource(uri = uri)
        except Exception, e:
            self.env.log.debug(e)
            self.setResponseCode(http.NOT_FOUND)
            return
        try:
            result = result.getData()
            result = result.encode("utf-8")
        except Exception, e:
            self.env.log.error(e)
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
            return
        return result
    
    def _getResourceList(self, uris=[]):
        fh = open(resource_filename(self.__module__,
                          "xml" + os.sep + "linklist.tmpl"))
        root = fh.read()
        fh.close()
        
        tmpl = """<link xlink:type="simple" xlink:href="%s">%s</link>"""
        doc = ""
        for uri in uris:
            # XXX: xml:base doesn't work!!!!
            doc += tmpl % ('/seishub'+uri, uri)
        return str(root % (self.path, doc))
    
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
    
    def _initRESTProcessors(self):
        """Return a list of available admin panels."""
        processor_list = ExtensionPoint(IRESTProcessor).extensions(self.env)
        self.processor_root = {}
        self.processors = {}
        for processor in processor_list:
            # skip processors without proper interfaces
            if not hasattr(processor, 'getProcessorId'):
                continue;
            options = processor.getProcessorId()
            # getProcessorId has exact 3 values in a tuple
            if not isinstance(options, tuple) or len(options)!=3:
                continue
            self.processors[options[0]] = processor
            self.processor_root[options[1]] = options[0]


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
    
    IntOption('rest', 'port', DEFAULT_REST_PORT, "REST port number.")
    
    def __init__(self, env):
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, port, RESTHTTPFactory(env))
        self.setName("REST")