# -*- coding: utf-8 -*-
"""
A HTTP/HTTPS server.
"""

from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption, BoolOption, Option
from seishub.defaults import HTTP_PORT, HTTPS_PORT, HTTPS_CERT_FILE, \
    HTTPS_PKEY_FILE, HTTP_LOG_FILE, HTTPS_LOG_FILE, ADMIN_THEME, DEFAULT_PAGES
from seishub.exceptions import InternalServerError, ForbiddenError, \
    SeisHubError
from seishub.processor import Processor, HEAD, getChildForRequest
from seishub.processor.interfaces import IFileSystemResource, IResource, \
    IStatical, IRESTResource
from seishub.util.path import addBase
from seishub.util.text import isInteger
from twisted.application import service
from twisted.application.internet import SSLServer #@UnresolvedImport
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.internet import threads, defer, ssl
from twisted.python.failure import Failure
from twisted.web import http, server, static
import StringIO
import errno
import gzip
import os
import urllib


__all__ = ['WebService']


RESOURCELIST_ROOT = """<?xml version="1.0" encoding="UTF-8"?>

<seishub xml:base="%s" xmlns:xlink="http://www.w3.org/1999/xlink">%s
</seishub>
"""

RESOURCELIST_NODE = """
  <%s category="%s"%s xlink:type="simple" xlink:href="%s"><![CDATA[%s]]></%s>"""


class WebRequest(Processor, http.Request):
    """
    A request via the HTTP/HTTPS protocol.
    """
    def __init__(self, channel, queued):
        self.env = channel.factory.env
        Processor.__init__(self, self.env)
        http.Request.__init__(self, channel, queued)
        self.notifications = []

    def isAuthenticatedUser(self):
        """
        XXX: this will change soon!
        """
        try:
            authenticated = self.env.auth.checkPassword(self.getUser(),
                                                        self.getPassword())
        except:
            return False
        return authenticated

    def getUser(self):
        return http.Request.getUser(self)

    def authenticate(self):
        """
        """
        self.setHeader('WWW-Authenticate', 'Basic realm="SeisHub"')
        self.setResponseCode(http.UNAUTHORIZED)
        self.write('Authentication required.')
        self.finish()

    def render(self):
        """
        Renders the requested resource returned from the self.process() method.
        """
        # check for logout
        if self.path == '/manage/logout':
            self.authenticate()
            return
        # traverse the resource tree
        try:
            result = getChildForRequest(self.env.tree, self)
        except SeisHubError, e:
            self.setResponseCode(e.code, e.message)
            self.env.log.http(e.code, e.message)
            self.write('')
            self.finish()
            return
        except Exception, e:
            self.env.log.error(e)
            self.write('')
            self.finish()
            return
        # set default HTTP headers
        self.setHeader('server', 'SeisHub ' + SEISHUB_VERSION)
        self.setHeader('date', http.datetimeToString())
        # result rendered?
        if result == server.NOT_DONE_YET:
            # resource takes care about rendering
            return
        # XXX: all or nothing - only authenticated are allowed to access
        # should be replaced with a much finer mechanism
        # URL, role and group based
        if not result.public and not self.isAuthenticatedUser():
            self.authenticate()
            return
        # check result and either render direct or in thread
        if IFileSystemResource.providedBy(result):
            # file system resources render direct 
            data = result.render(self)
            if result.folderish:
                # check for default page
                for id in DEFAULT_PAGES:
                    if id in data and not data[id].folderish:
                        self.redirect(addBase(self.path, id))
                return self._renderFolder(data)
            else:
                return self._renderFileResource(data)
        elif IStatical.providedBy(result):
            # static resources render direct
            data = result.render(self)
            if isinstance(data, basestring):
                return self._renderResource(data)
            elif isinstance(data, dict):
                return self._renderFolder(data)
        elif IRESTResource.providedBy(result):
            # REST resource render in thread
            d = threads.deferToThread(result.render, self)
            d.addCallback(self._cbSuccess)
            d.addErrback(self._cbFailed)
            return server.NOT_DONE_YET
        elif IResource.providedBy(result):
            # all other resources render in thread
            d = threads.deferToThread(result.render, self)
            d.addCallback(self._cbSuccess)
            d.addErrback(self._cbFailed)
            return server.NOT_DONE_YET
        msg = "I don't know how to handle this resource type %s"
        raise InternalServerError(msg % type(result))

    def _cbSuccess(self, result):
        if isinstance(result, dict):
            # a folderish resource
            return self._renderFolder(result)
        elif isinstance(result, basestring):
            # already some textual result
            return self._renderResource(result)
        else:
            # some object - a non-folderish resource
            d = threads.deferToThread(result.render, self)
            d.addCallback(self._renderResource)
            d.addErrback(self._cbFailed)
            return server.NOT_DONE_YET

    def _cbFailed(self, failure):
        if not isinstance(failure, Failure):
            raise
        if 'seishub.exceptions.SeisHubError' not in failure.parents:
            # we got something unhandled
            self.env.log.error(failure.getTraceback())
            self.setResponseCode(http.INTERNAL_SERVER_ERROR)
        else:
            # this is a SeisHubError
            self.setResponseCode(failure.value.code, failure.value.message)
            self.env.log.http(failure.value.code, failure.value.message)
        self.write('')
        self.finish()
        return

    def _renderFileResource(self, obj):
        """
        Renders a object implementing L{IFileResource}.
        """
        # refresh stats
        obj.restat()
        # try to open
        try:
            fp = obj.open()
        except IOError, e:
            if e[0] == errno.EACCES:
                msg = "Can not access item %s."
                raise ForbiddenError(msg % str(obj.path))
            raise
        # check if cached
        last_modified = int(obj.getModificationTime())
        if self.setLastModified(last_modified) is http.CACHED:
            self.finish()
            return
        # content type + encoding
        obj.type, obj.enc = static.getTypeAndEncoding(obj.basename(),
                                                      obj.content_types,
                                                      obj.content_encodings,
                                                      obj.default_type)
        if obj.type:
            self.setHeader('content-type', obj.type)
        if obj.enc:
            self.setHeader('content-encoding', obj.enc)
        # file size
        fsize = size = obj.getsize()
        self.setHeader('content-length', str(fsize))
        if self.method == HEAD:
            self.write('')
            self.finish()
            return
        # accept range
        self.setHeader('accept-ranges', 'bytes')
        range = self.getHeader('range')
        # a request for partial data, e.g. Range: bytes=160694272-
        if range and 'bytes=' in range and '-' in range.split('=')[1]:
            parts = range.split('bytes=')[1].strip().split('-')
            if len(parts) == 2:
                start = parts[0]
                end = parts[1]
                if isInteger(start):
                    fp.seek(int(start))
                if isInteger(end):
                    end = int(end)
                    size = end
                else:
                    end = size
                self.setResponseCode(http.PARTIAL_CONTENT)
                self.setHeader('content-range', "bytes %s-%s/%s " % (
                     str(start), str(end), str(size)))
                #content-length should be the actual size of the stuff we're
                #sending, not the full size of the on-server entity.
                fsize = end - int(start)
                self.setHeader('content-length', str(fsize))
        # start the file transfer
        static.FileTransfer(fp, fsize, self)
        # and make sure the connection doesn't get closed
        return server.NOT_DONE_YET

    def _renderResource(self, data=''):
        """
        Renders a resource.
        
        @param data: content of the document to be rendered
        @return:     None
        """
        # set default content type to XML
        if 'content-type' not in self.headers:
            self.setHeader('content-type', 'application/xml; charset=UTF-8')
        # gzip encoding
        encoding = self.getHeader("accept-encoding")
        if encoding and encoding.find("gzip") >= 0:
            zbuf = StringIO.StringIO()
            zfile = gzip.GzipFile(None, 'wb', 9, zbuf)
            zfile.write(data)
            zfile.close()
            self.setHeader("content-encoding", "gzip")
            data = zbuf.getvalue()
        # set header
        self.setHeader('content-length', str(len(data)))
        # write output
        if self.method == HEAD:
            self.write('')
        else:
            self.write(data)
        self.finish()

    def _renderFolder(self, children={}):
        """
        Renders a folderish resource.
        
        @param children: dict of child objects implementing L{IResource}
        @return:         None
        """
        ids = sorted(children)
        # generate a list of standard elements
        data = ''
        for id in ids:
            obj = children.get(id)
            tag = 'resource'
            category = obj.category
            # skip hidden objects
            if obj.hidden:
                continue
            if obj.folderish:
                tag = 'folder'
                size = ''
            else:
                size = ' size="%d"' % (obj.getMetadata().get('size', 0))
#            # id may be unicode object -> create an UTF-8 encoded string
            if isinstance(id, unicode):
                id = id.encode('utf-8')
            # we need to make the URL web safe
            url = urllib.quote(addBase(self.path, id))
            data += RESOURCELIST_NODE % (tag, category, size, url, id, tag)
        data = str(RESOURCELIST_ROOT % (str(self.env.getRestUrl()), data))
        # set default content type to XML
        if 'content-type' not in self.headers:
            self.setHeader('content-type', 'application/xml; charset=UTF-8')
        # parse request headers for output type
        format = self.args.get('format', [None])[0] or \
                 self.args.get('output', [None])[0]
        # handle output/format conversion
        if format:
            # fetch a xslt document object
            reg = self.env.registry
            xslt = reg.stylesheets.get(package_id='seishub',
                                       resourcetype_id='stylesheet',
                                       type='resourcelist.%s' % format)
            if len(xslt):
                xslt = xslt[0]
                data = xslt.transform(data)
                if xslt.content_type:
                    self.setHeader('content-type',
                                   xslt.content_type + '; charset=UTF-8')
            else:
                msg = "There is no stylesheet for requested format %s."
                self.env.log.debug(msg % format)
        # gzip encoding
        encoding = self.getHeader("accept-encoding")
        if encoding and encoding.find("gzip") >= 0:
            zbuf = StringIO.StringIO()
            zfile = gzip.GzipFile(None, 'wb', 9, zbuf)
            zfile.write(data)
            zfile.close()
            self.setHeader("content-encoding", "gzip")
            data = zbuf.getvalue()
        # set header
        self.setHeader('content-length', str(len(data)))
        # write output
        if self.method == HEAD:
            self.write('')
        else:
            self.write(data)
        self.finish()

    def notifyFinish(self):
        """
        Notify when finishing the request
        
        @return: A deferred. The deferred will be triggered when the request 
            is finished -- with a C{None} value if the request finishes 
            successfully or with an error if the request is stopped by the 
            client.
        """
        self.notifications.append(defer.Deferred())
        return self.notifications[-1]

    def connectionLost(self, reason):
        for d in self.notifications:
            d.errback(reason)
        self.notifications = []

    def finish(self):
        if not self.finished:
            http.Request.finish(self)
        for d in self.notifications:
            d.callback(None)
        self.notifications = []


class WebServiceFactory(http.HTTPFactory):
    """
    Factory for the HTTP/HTTPS Server.
    """
    def __init__(self, env, log_file='', timeout=None):
        self.env = env
        http.HTTPFactory.__init__(self, log_file, timeout)
        self.protocol.requestFactory = WebRequest


class HTTPService(TCPServer):
    """
    HTTP Service.
    """
    def __init__(self, env):
        self.env = env
        http_port = env.config.getint('web', 'http_port') or HTTP_PORT
        log_file = env.config.get('web', 'http_log_file') or None
        if not os.path.isabs(log_file):
            log_file = os.path.join(self.env.config.path, log_file)
        factory = WebServiceFactory(env, log_file)
        TCPServer.__init__(self, http_port, factory)


class HTTPSService(SSLServer):
    """
    HTTPS Service.
    """
    def __init__(self, env):
        self.env = env
        https_port = env.config.getint('web', 'https_port') or HTTPS_PORT
        priv, cert = self._getCertificates()
        context = ssl.DefaultOpenSSLContextFactory(str(priv), str(cert))
        log_file = env.config.get('web', 'https_log_file') or None
        if not os.path.isabs(log_file):
            log_file = os.path.join(self.env.config.path, log_file)
        factory = WebServiceFactory(env, log_file)
        SSLServer.__init__(self, https_port, factory, context, 1)

    def _getCertificates(self):
        """
        Fetch HTTPS certificate paths from configuration.
        
        return: Paths to pkey and cert files.
        """
        pkey_file = self.env.config.get('web', 'https_pkey_file')
        cert_file = self.env.config.get('web', 'https_cert_file')
        if not os.path.isabs(pkey_file):
            pkey_file = os.path.join(self.env.config.path, pkey_file)
        if not os.path.isabs(cert_file):
            cert_file = os.path.join(self.env.config.path, cert_file)
        # test if certificates exist
        msg = "HTTPS certificate file %s is missing!"
        if not os.path.isfile(cert_file):
            self.env.log.warn(msg % cert_file)
            return self._generateCertificates()
        if not os.path.isfile(pkey_file):
            self.env.log.warn(msg % pkey_file)
            return self._generateCertificates()
        return pkey_file, cert_file

    def _generateCertificates(self):
        """
        Generates new self-signed certificates.
        
        return: Paths to pkey and cert files.
        """
        from seishub.util import certgen
        from OpenSSL import crypto
        # generate
        msg = "Generating new certificate files for the HTTPS service ..."
        self.env.log.warn(msg)
        timespan = (0, 60 * 60 * 24 * 365 * 5) # five years
        pkey_file = os.path.join(self.env.config.path, HTTPS_PKEY_FILE)
        cert_file = os.path.join(self.env.config.path, HTTPS_CERT_FILE)
        # CA
        cakey = certgen.createKeyPair(certgen.TYPE_RSA, 1024)
        careq = certgen.createCertRequest(cakey, CN='SeisHub CA')
        cacert = certgen.createCertificate(careq, (careq, cakey), 0, timespan)
        # pkey
        pkey = certgen.createKeyPair(certgen.TYPE_RSA, 1024)
        server_pkey = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
        file(pkey_file, 'w').write(server_pkey)
        msg = "Private key file %s has been created."
        self.env.log.warn(msg % pkey_file)
        # cert
        req = certgen.createCertRequest(pkey, CN='localhost:8443')
        cert = certgen.createCertificate(req, (cacert, cakey), 1, timespan)
        server_cert = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        file(cert_file, 'w').write(server_cert)
        msg = "Certificate file %s has been created."
        self.env.log.warn(msg % cert_file)
        # write config
        self.env.config.set('web', 'https_pkey_file', pkey_file)
        self.env.config.set('web', 'https_cert_file', cert_file)
        self.env.config.save()
        return pkey_file, cert_file


class WebService(service.MultiService):
    """
    MultiService for the HTTP/HTTPS server.
    """
    service_id = "web"

    BoolOption('web', 'autostart', True, "Run HTTP/HTTPS service on start-up.")
    IntOption('web', 'http_port', HTTP_PORT, "HTTP port number.")
    IntOption('web', 'https_port', HTTPS_PORT, "HTTPS port number.")
    Option('web', 'http_log_file', HTTP_LOG_FILE, "HTTP access log file.")
    Option('web', 'https_log_file', HTTPS_LOG_FILE, "HTTPS access log file.")
    Option('web', 'https_pkey_file', HTTPS_PKEY_FILE, "Private key file.")
    Option('web', 'https_cert_file', HTTPS_CERT_FILE, "Certificate file.")
    Option('web', 'admin_theme', ADMIN_THEME, "Default administration theme.")

    def __init__(self, env):
        self.env = env
        service.MultiService.__init__(self)
        self.setName('HTTP/HTTPS Server')
        self.setServiceParent(env.app)

        http_service = HTTPService(env)
        http_service.setName("HTTP Server")
        self.addService(http_service)

        https_service = HTTPSService(env)
        https_service.setName("HTTPS Server")
        self.addService(https_service)

    def privilegedStartService(self):
        if self.env.config.getbool('web', 'autostart'):
            service.MultiService.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('web', 'autostart'):
            service.MultiService.startService(self)

    def stopService(self):
        if self.running:
            service.MultiService.stopService(self)
