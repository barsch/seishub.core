# -*- coding: utf-8 -*-

import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET, MOVE
from seishub.packages.processor import MAX_URI_LENGTH
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
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        PackageInstaller.install(self.env)
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_moveWithoutDestinationHeader(self):
        """WebDAV HTTP MOVE request must submit a Destination header."""
        proc = Processor(self.env)
        try:
            proc.run(MOVE, '/test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithoutCompleteDestinationPath(self):
        """Destination header must be the complete path to new destination."""
        proc = Processor(self.env)
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': '/test/notvc/muh.xml'})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithOversizedDestinationPath(self):
        """Destination path is restricted by MAX_URI_LENGTH."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/test/notvc/' + 'a'*(MAX_URI_LENGTH+1)
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.REQUEST_URI_TOO_LONG)
    
    def test_moveToDifferentDirectory(self):
        """SeisHub allows moving resources only in the same directory."""
        proc = Processor(self.env)
        # try different resource type
        uri = self.env.getRestUrl() + '/test/vc/test2.xml'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # try non existing resource type
        uri = self.env.getRestUrl() + '/muh/kuh/test2.xml'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToDirectory(self):
        """SeisHub expects as destination a full filename."""
        proc = Processor(self.env)
        # directory only with trailing slash
        uri = self.env.getRestUrl() + '/test/vc/'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # without trailing slash
        uri = self.env.getRestUrl() + '/test/vc'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToNewResource(self):
        """The resource was moved successfully and a new resource was created 
        at the specified destination URI.
        """
        proc = Processor(self.env)
        # create a default document
        proc.run(PUT, '/test/notvc/test.xml', StringIO(XML_DOC))
        # move
        uri = self.env.getRestUrl() + '/test/notvc/new.xml'
        data = proc.run(MOVE, '/test/notvc/test.xml', 
                        received_headers = {'Destination': uri})
        # test if right response code
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.CREATED)
        # test if location header is set
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertEquals(location, uri)
        # get original resource
        try:
            proc.run(GET, '/test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # get new resource
        proc.run(GET, '/test/notvc/new.xml')
        # revert move
        uri = self.env.getRestUrl() + '/test/notvc/test.xml'
        proc.run(MOVE, '/test/notvc/new.xml', 
                 received_headers = {'Destination': uri})
        # get original resource
        proc.run(GET, '/test/notvc/test.xml')
        # get new resource 
        try:
            proc.run(GET, '/test/notvc/new.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # remove default document
        proc.run(DELETE, '/test/notvc/test.xml')
        
    
    def test_moveRevision(self):
        # FORBIDDEN
        pass
    
    def test_moveToExistingResource(self):
        #204 (No Content)    The resource was moved successfully to a pre-existing destination URI.
        pass
    
    def test_moveToSameURI(self):
        """The source URI and the destination URI must not be the same."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/test/notvc/test.xml'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToInvalidResourcename(self):
        """SeisHub restricts the destination filenames to distinct between 
        ~mappers, @aliases and .properties.
        """
        proc = Processor(self.env)
        # XXX: not working yet - no exception raised from catalog!
        # starting tilde (~)
        uri = self.env.getRestUrl() + '/test/notvc/~test'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting dot (.)
        uri = self.env.getRestUrl() + '/test/notvc/.test'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting at sign (@)
        uri = self.env.getRestUrl() + '/test/notvc/@test'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting underscore (_)
        uri = self.env.getRestUrl() + '/test/notvc/_test'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting minus (-)
        uri = self.env.getRestUrl() + '/test/notvc/-test'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # but this should go
        uri = self.env.getRestUrl() + '/test/notvc/Aaz09_-.xml'
        proc.run(MOVE, '/test/notvc/test.xml', 
                 received_headers = {'Destination': uri})
        # and revert again
        uri = self.env.getRestUrl() + '/test/notvc/test.xml'
        proc.run(MOVE, '/test/notvc/Aaz09_-.xml', 
                 received_headers = {'Destination': uri})
    
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
        proc = Processor(self.env)
        uri = 'http://somewhere:8080/test/notvc/test.xml'
        try:
            proc.run(MOVE, '/test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_GATEWAY)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorMOVETest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')