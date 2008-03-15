# -*- coding: utf-8 -*-

from twisted.web import http
from twisted.application import internet
from twisted.internet import threads

from seishub.defaults import DEFAULT_REST_PORT
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption


class RESTRequest(http.Request):
    """A HTTP request."""
    
    def __init__(self, channel, queued):
        http.Request.__init__(self, channel, queued)
    
    def process(self):
        if self.path == '/':
            self.write("I am a REST server - serving atm nothing ;)")
            self.finish()
            return
        
        #process in thread
        d = threads.deferToThread(self._process)
        d.addErrback(self._processingFailed)
    
    def _process(self):
        #use method to identify use case
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
        """Handles a HTTP GET request."""
        # try to get resource from catalog directly
        result = self._isResource()
        if result:
            try:
                result = result.getData()
                result = result.encode("utf-8")
            except Exception, e:
                self.env.log.error(e)
                self.setResponseCode(http.INTERNAL_SERVER_ERROR)
                self.finish()
                return
            #write resource data as response
            self.setHeader('server', 'SeisHub '+ SEISHUB_VERSION)
            self.setHeader('date', http.datetimeToString())
            self.setHeader('content-type', "text/xml; charset=UTF-8")
            self.setHeader('content-length', str(len(result)))
            self.setResponseCode(http.OK)
            self.write(result)
            self.finish()
        # test if 
        elif self.env.catalog.aliases.get(self.path):
            self.setResponseCode(http.OK)
            print "----------------------------------"
            print self.env.catalog.query(self.env.catalog.aliases[self.path])
            #self.write(str(self.env.catalog.aliases[self.path]))
            self.finish()
        else:
            self.setResponseCode(http.NOT_FOUND)
            self.finish()

    
    def _isResource(self):
        try:
            result = self.env.catalog.getResource(uri = self.path)
        except:
            return False
        return result
    
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