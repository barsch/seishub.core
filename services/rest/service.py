# -*- coding: utf-8 -*-

import os
import string
from urllib import unquote

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub.defaults import REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption
from seishub.util.xml import XmlTreeDoc, XmlStylesheet
from seishub.services.processor import Processor


class RESTRequest(Processor, http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
        Processor.__init__(self, self.env)
    
    def process(self):
        """Start processing a request."""
        # post process self.path
        self.postpath = map(unquote, string.split(self.path[1:], '/'))
        #fetch method
        self.method = self.method.upper()
        # fetch output type
        self.output = self.args.get('output', None)
        
        # process in thread
        d = threads.deferToThread(self.processThread)
        d.addErrback(self.processingFailed)
    
    def processThread(self):
        data = Processor.process(self)
        self.write(str(data))
        self.setResponseCode(http.OK)
        self.finish()
        return
        
        
        
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
    
    def setHeaders(self, content=None, content_type='text/xml'):
        """Sets standard HTTP headers."""
        self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        if content:
            self.setHeader('content-type', content_type+"; charset=UTF-8")
            self.setHeader('content-length', str(len(str(content))))
   
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
    
    def formatResource(self, uri):
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
    
    def formatResourceList(self, uris=[], base=''):
        root = open(resource_filename(self.__module__,"xml" + os.sep + 
                                      "linklist.tmpl")).read()
        tmpl = """<link xlink:type="simple" xlink:href="%s">%s</link>"""
        doc = ""
        for uri in uris:
            # XXX: xml:base doesn't work!!!!
            doc += tmpl % (base + '/' + uri, uri)
        return str(root % (self.path, doc))
    
    def processingFailed(self, reason):
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


class RESTServiceFactory(http.HTTPFactory):
    """Factory for HTTP Server."""
    protocol = RESTHTTPChannel
    
    def __init__(self, env, logPath=None, timeout=None):
        http.HTTPFactory.__init__(self, logPath, timeout)
        self.env = env
        self.protocol.env = env


class RESTService(internet.TCPServer):
    """Service for REST HTTP Server."""
    
    IntOption('rest', 'port', REST_PORT, "REST port number.")
    
    def __init__(self, env):
        port = env.config.getint('rest', 'port')
        internet.TCPServer.__init__(self, port, RESTServiceFactory(env))
        self.setName("REST")
        self.setServiceParent(env.app)