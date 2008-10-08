# -*- coding: utf-8 -*-

import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET, MOVE
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import PackageInstaller


XML_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>
"""


class AResourceType(Component):
    """A non version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorMOVETest(SeisHubEnvironmentTestCase):
    """Test case for HTTP MOVE processing."""
    
    def setUp(self):
        # setup components
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        PackageInstaller.install(self.env)
        # setup some default resources
        self.proc = Processor(self.env)
        self.proc.run(PUT, '/test/vc/test.xml', StringIO(XML_DOC))
        # XXX: BUG
        #self.proc.run(POST, '/test/vc/test.xml', StringIO(XML_DOC))
        #self.proc.run(POST, '/test/vc/test.xml', StringIO(XML_DOC))
        #self.proc.run(PUT, '/test/notvc/test.xml', StringIO(XML_DOC))
        # XXX: but this works???
        self.proc.run(PUT, '/test/notvc/test.xml', StringIO(XML_DOC))
        self.proc.run(POST, '/test/vc/test.xml', StringIO(XML_DOC))
        self.proc.run(POST, '/test/vc/test.xml', StringIO(XML_DOC))
    
    def tearDown(self):
        # remove default resources
        self.proc.run(DELETE, '/test/vc/test.xml')
        self.proc.run(DELETE, '/test/notvc/test.xml')
        # disable components
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_moveWithoutDestinationHeader(self):
        """WebDAV HTTP MOVE request must submit a Destination header."""
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithoutCompleteDestinationPath(self):
        """Destination header must be the complete path to new destination."""
        rh = {'Destination': '/test/notvc/test2.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveToDifferentDirectory(self):
        """SeisHub allows moving resources only in the same directory."""
        # try different resource type
        rh = {'Destination': self.env.getRestUrl() + '/test/vc/test2.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # try non existing resource type
        rh = {'Destination': self.env.getRestUrl() + '/muh/kuh/test2.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToDirectory(self):
        """SeisHub expects as destination a full filename."""
        # directory only with trailing slash
        rh = {'Destination': self.env.getRestUrl() + '/test/vc/'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # without trailing slash
        rh = {'Destination': self.env.getRestUrl() + '/test/vc'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToNewResource(self):
        """The resource was moved successfully and a new resource was created 
        at the specified destination URI.
        """
        # move
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/new.xml'}
        self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
        # get original resource
        try:
            self.proc.run(GET, '/test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # get new resource
        self.proc.run(GET, '/test/notvc/new.xml')
        # revert move
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/test.xml'}
        self.proc.run(MOVE, '/test/notvc/new.xml', received_headers = rh)
        # get original resource
        self.proc.run(GET, '/test/notvc/test.xml')
        # get new resource 
        try:
            self.proc.run(GET, '/test/notvc/new.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_moveRevision(self):
        # FORBIDDEN
        pass
    
    def test_moveToExistingResource(self):
        #204 (No Content)    The resource was moved successfully to a pre-existing destination URI.
        pass
    
    def test_moveToSameURI(self):
        """The source URI and the destination URI must not be the same."""
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToInvalidResourcename(self):
        """SeisHub restricts the destination filenames to distinct between 
        ~mappers, @aliases and .properties.
        """
        # XXX: not working yet - no exception raised from catalog!
        # starting tilde (~)
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/~test'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        #except ProcessorError, e:
        #    self.assertEqual(e.code, http.CONFLICT)
        except:
            import pdb;pdb.set_trace()
            pass
        # starting dot (.)
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/.test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting at sign (@)
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/@test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting underscore (_)
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/_test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting minus (-)
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/-test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # but this should go
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/Aaz09_-.xml'}
        self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
        # and revert again
        rh = {'Destination': self.env.getRestUrl() + '/test/notvc/test.xml'}
        self.proc.run(MOVE, '/test/notvc/Aaz09_-.xml', received_headers = rh)
    
    def test_canNotCreateResource(self):
        #409 (Conflict)    A resource cannot be created at the destination URI until one or more intermediate collections are created.
        pass
    
    def test_failingPrecondition(self):
        #412 (Precondition Failed)    Either the Overwrite header is "F" and the state of the destination resource is not null, or the method was used in a Depth: 0 transaction.
        pass
    
    def test_moveLockedResource(self):
        #423 (Locked)    The destination resource is locked.
        pass
    
    def test_moveToDifferentServer(self):
        """The destination URI is located on a different server."""
        rh = {'Destination': 'http://somewhere:8080/test/notvc/test.xml'}
        try:
            self.proc.run(MOVE, '/test/notvc/test.xml', received_headers = rh)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_GATEWAY)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorMOVETest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')