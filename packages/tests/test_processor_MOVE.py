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


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class AResourceType(Component):
    """A non version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'move-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'move-test'
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
            proc.run(MOVE, '/move-test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithoutAbsoluteDestination(self):
        """Destination header must be the absolute path to new destination."""
        proc = Processor(self.env)
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': '/test/notvc/muh.xml'})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithOversizedDestination(self):
        """Destination path is restricted to MAX_URI_LENGTH chars."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/move-test/notvc/' + \
              'a' * (MAX_URI_LENGTH + 1)
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.REQUEST_URI_TOO_LONG)
    
    def test_moveToOtherResourceType(self):
        """SeisHub allows moving resources only to the same resource type."""
        proc = Processor(self.env)
        # try different resource type
        uri = self.env.getRestUrl() + '/move-test/vc/test2.xml'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToNotExistingResourceType(self):
        """SeisHub allows moving resources only to existing resource types."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/muh/kuh/test2.xml'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveWithoutFilename(self):
        """SeisHub expects as destination a full filename."""
        proc = Processor(self.env)
        # directory only with trailing slash
        uri = self.env.getRestUrl() + '/move-test/vc/'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # without trailing slash
        uri = self.env.getRestUrl() + '/move-test/vc'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToNewResource(self):
        """Resource was moved successfully to the specified destination URI."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/notvc/test.xml', StringIO(XML_DOC))
        # move
        uri = self.env.getRestUrl() + '/move-test/notvc/new.xml'
        data = proc.run(MOVE, '/move-test/notvc/test.xml', 
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
            proc.run(GET, '/move-test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # get new resource
        data = proc.run(GET, '/move-test/notvc/new.xml')
        self.assertEqual(data, XML_DOC)
        # revert move
        uri = self.env.getRestUrl() + '/move-test/notvc/test.xml'
        proc.run(MOVE, '/move-test/notvc/new.xml', 
                 received_headers = {'Destination': uri})
        # get original resource
        proc.run(GET, '/move-test/notvc/test.xml')
        # get new resource 
        try:
            proc.run(GET, '/move-test/notvc/new.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # remove resource
        proc.run(DELETE, '/move-test/notvc/test.xml')
    
    def test_moveRevisionToRevision(self):
        """SeisHub does not allow to move revisions to revisions."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test.xml', StringIO(XML_DOC))
        # try to move revision 2 to revision 1 
        uri = self.env.getRestUrl() + '/move-test/vc/test.xml/1'
        try:
            proc.run(MOVE, '/move-test/vc/test.xml/2', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/move-test/vc/test.xml')
    
    def test_moveRevisionToNewResource(self):
        """SeisHub does not allow to move revisions to resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test.xml', StringIO(XML_DOC))
        # try to move revision 1 to another uri 
        uri = self.env.getRestUrl() + '/move-test/vc/muh.xml'
        try:
            proc.run(MOVE, '/move-test/vc/test.xml/1', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/move-test/vc/test.xml')
    
    def test_moveToExistingRevision(self):
        """SeisHub does not allow to move resources to revisions."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/vc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        # try to overwrite the existing revision 1
        uri = self.env.getRestUrl() + '/move-test/vc/test2.xml/1'
        try:
            proc.run(MOVE, '/move-test/vc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/vc/test1.xml')
        proc.run(DELETE, '/move-test/vc/test2.xml')
    
    def test_moveToNewRevision(self):
        """SeisHub does not allow to move a resource to a new revision."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/vc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/vc/test2.xml', StringIO(XML_DOC))
        # try to create a new revision 4
        uri = self.env.getRestUrl() + '/move-test/vc/test2.xml/4'
        try:
            proc.run(MOVE, '/move-test/vc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/vc/test1.xml')
        proc.run(DELETE, '/move-test/vc/test2.xml')
    
    def test_moveToExistingResource(self):
        """SeisHub does not allow to overwrite existing resources."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/notvc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/notvc/test2.xml', StringIO(XML_DOC))
        # try to overwrite test2.xml 
        uri = self.env.getRestUrl() + '/move-test/notvc/test2.xml'
        try:
            proc.run(MOVE, '/move-test/notvc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/vc/test1.xml')
        proc.run(DELETE, '/move-test/vc/test2.xml')
    
    def test_moveToSameURI(self):
        """The source URI and the destination URI must not be the same."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/move-test/notvc/test.xml'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToInvalidResourcename(self):
        """Destination file name may not start with '~', '@', '.', '_' or '-'.
        
        SeisHub restricts the destination filename to distinct between 
        ~mappers, @aliases and .properties.
        """
        proc = Processor(self.env)
        # XXX: not working yet - no exception raised from catalog!
        # starting tilde (~)
        uri = self.env.getRestUrl() + '/move-test/notvc/~test'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting dot (.)
        uri = self.env.getRestUrl() + '/move-test/notvc/.test'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting at sign (@)
        uri = self.env.getRestUrl() + '/move-test/notvc/@test'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting underscore (_)
        uri = self.env.getRestUrl() + '/move-test/notvc/_test'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting minus (-)
        uri = self.env.getRestUrl() + '/move-test/notvc/-test'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # but this should go
        uri = self.env.getRestUrl() + '/move-test/notvc/Aaz09_-.xml'
        proc.run(MOVE, '/move-test/notvc/test.xml', 
                 received_headers = {'Destination': uri})
        # and revert again
        uri = self.env.getRestUrl() + '/move-test/notvc/test.xml'
        proc.run(MOVE, '/move-test/notvc/Aaz09_-.xml', 
                 received_headers = {'Destination': uri})
    
    def test_canNotCreateResource(self):
        # 409 (Conflict)    A resource cannot be created at the destination URI
        # until one or more intermediate collections are created.
        pass
    
    def test_failingPrecondition(self):
        # 412 (Precondition Failed)    Either the Overwrite header is "F" and
        # the state of the destination resource is not null, or the method was
        # used in a Depth: 0 transaction.
        pass
    
    def test_moveLockedResource(self):
        # XXX: not implemented yet
        #423 (Locked)    The destination resource is locked.
        pass
    
    def test_moveToDifferentServer(self):
        """The destination URI is located on a different server."""
        proc = Processor(self.env)
        uri = 'http://somewhere:8080/move-test/notvc/test.xml'
        try:
            proc.run(MOVE, '/move-test/notvc/test.xml', 
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