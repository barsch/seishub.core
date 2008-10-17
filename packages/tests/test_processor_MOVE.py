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


class ProcessorMOVETestSuite(SeisHubEnvironmentTestCase):
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
            proc.run(MOVE, '/move-test/xml/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithoutAbsoluteDestination(self):
        """Destination header must be the absolute path to new destination."""
        proc = Processor(self.env)
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': '/test/notvc/muh.xml'})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_REQUEST)
    
    def test_moveWithOversizedDestination(self):
        """Destination path is restricted to MAX_URI_LENGTH chars."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/' + \
              'a' * (MAX_URI_LENGTH + 1)
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.REQUEST_URI_TOO_LONG)
    
    def test_moveToOtherResourceType(self):
        """SeisHub allows moving resources only to the same resource type."""
        proc = Processor(self.env)
        # try different resource type
        uri = self.env.getRestUrl() + '/move-test/xml/vc/test2.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToInvalidResourceTypePath(self):
        """Expecting a xml directory between package and resource type."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/xml/notvc/test.xml', StringIO(XML_DOC))
        # try different resource type
        uri = self.env.getRestUrl() + '/move-test/muh/notvc/test2.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/move-test/xml/notvc/test.xml')
    
    def test_moveToNonExistingResourceType(self):
        """SeisHub allows moving resources only to existing resource types."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/muh/xml/kuh/test2.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveWithoutFilename(self):
        """SeisHub expects as destination a full filename."""
        proc = Processor(self.env)
        # directory only with trailing slash
        uri = self.env.getRestUrl() + '/move-test/xml/vc/'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # without trailing slash
        uri = self.env.getRestUrl() + '/move-test/xml/vc'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToNewResource(self):
        """Resource was moved successfully to the specified destination URI."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/xml/notvc/test.xml', StringIO(XML_DOC))
        # move
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/new.xml'
        data = proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
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
            proc.run(GET, '/move-test/xml/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # get new resource
        data = proc.run(GET, '/move-test/xml/notvc/new.xml')
        self.assertEqual(data, XML_DOC)
        # revert move
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/test.xml'
        proc.run(MOVE, '/move-test/xml/notvc/new.xml', 
                 received_headers = {'Destination': uri})
        # get original resource
        proc.run(GET, '/move-test/xml/notvc/test.xml')
        # get new resource 
        try:
            proc.run(GET, '/move-test/xml/notvc/new.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # remove resource
        proc.run(DELETE, '/move-test/xml/notvc/test.xml')
    
    def test_moveRevisionToRevision(self):
        """SeisHub does not allow to move revisions to revisions."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        # try to move revision 2 to revision 1 
        uri = self.env.getRestUrl() + '/move-test/vc/test.xml/1'
        try:
            proc.run(MOVE, '/move-test/xml/vc/test.xml/2', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/move-test/xml/vc/test.xml')
    
    def test_moveRevisionToNewResource(self):
        """SeisHub does not allow to move revisions to resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test.xml', StringIO(XML_DOC))
        # try to move revision 1 to another uri 
        uri = self.env.getRestUrl() + '/move-test/vc/muh.xml'
        try:
            proc.run(MOVE, '/move-test/xml/vc/test.xml/1', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/move-test/xml/vc/test.xml')
    
    def test_moveToExistingRevision(self):
        """SeisHub does not allow to move resources to revisions."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/xml/vc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        # try to overwrite the existing revision 1
        uri = self.env.getRestUrl() + '/move-test/xml/vc/test2.xml/1'
        try:
            proc.run(MOVE, '/move-test/xml/vc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/xml/vc/test1.xml')
        proc.run(DELETE, '/move-test/xml/vc/test2.xml')
    
    def test_moveToNewRevision(self):
        """SeisHub does not allow to move a resource to a new revision."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/xml/vc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        proc.run(POST, '/move-test/xml/vc/test2.xml', StringIO(XML_DOC))
        # try to create a new revision 4
        uri = self.env.getRestUrl() + '/move-test/xml/vc/test2.xml/4'
        try:
            proc.run(MOVE, '/move-test/xml/vc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/xml/vc/test1.xml')
        proc.run(DELETE, '/move-test/xml/vc/test2.xml')
    
    def test_moveToExistingResource(self):
        """XXX: SeisHub does not allow to overwrite existing resources."""
        proc = Processor(self.env)
        # create resources
        proc.run(PUT, '/move-test/xml/notvc/test1.xml', StringIO(XML_DOC))
        proc.run(PUT, '/move-test/xml/notvc/test2.xml', StringIO(XML_DOC))
        # try to overwrite test2.xml 
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/test2.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test1.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            # XXX: BUG - see ticket #61 - processor should raise FORBIDDEN
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resources
        proc.run(DELETE, '/move-test/xml/vc/test1.xml')
        proc.run(DELETE, '/move-test/xml/vc/test2.xml')
    
    def test_moveBuiltinResource(self):
        """SeisHub builtin resources can't be renamed or moved."""
        proc = Processor(self.env)
        # fetch a seishub stylesheet
        data = proc.run(GET, '/seishub/xml/stylesheet')
        uri = str(data.get('resource')[0])
        to_uri = self.env.getRestUrl() + '/seishub/xml/stylesheet/test.xml' 
        try:
            proc.run(MOVE, uri, received_headers = {'Destination': to_uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToSameURI(self):
        """The source URI and the destination URI must not be the same."""
        proc = Processor(self.env)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/test.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_moveToInvalidResourcename(self):
        """XXX: Destination file name may not start with '~', '@', '.', '_' or '-'.
        
        SeisHub restricts the destination filename to distinct between 
        ~mappers, @aliases and .properties.
        """
        proc = Processor(self.env)
        # XXX: BUG see ticket #36 - no exception raised from catalog!
        # starting tilde (~)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/~test'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting dot (.)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/.test'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting at sign (@)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/@test'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting underscore (_)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/_test'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # starting minus (-)
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/-test'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.CONFLICT)
        # but this should go
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/Aaz09_-.xml'
        proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                 received_headers = {'Destination': uri})
        # and revert again
        uri = self.env.getRestUrl() + '/move-test/xml/notvc/test.xml'
        proc.run(MOVE, '/move-test/xml/notvc/Aaz09_-.xml', 
                 received_headers = {'Destination': uri})
    
    def test_moveLockedResource(self):
        # XXX: see ticket #38 - not implemented yet
        #423 (Locked)    The destination resource is locked.
        pass
    
    def test_moveToDifferentServer(self):
        """The destination URI is located on a different server."""
        proc = Processor(self.env)
        uri = 'http://somewhere:8080/move-test/xml/notvc/test.xml'
        try:
            proc.run(MOVE, '/move-test/xml/notvc/test.xml', 
                     received_headers = {'Destination': uri})
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.BAD_GATEWAY)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorMOVETestSuite, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')