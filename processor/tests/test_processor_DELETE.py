# -*- coding: utf-8 -*-

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor import Processor, PUT, POST, DELETE, GET
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


XML_VCDOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """A non version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'delete-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'delete-test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorDELETETestSuite(SeisHubEnvironmentTestCase):
    """Test case for HTTP DELETE processing."""
    
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_deletePackage(self):
        """SeisHub processor does not allow deletion of packages."""
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteResourceType(self):
        """SeisHub processor does not allow deletion of resource types."""
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/notvc')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/notvc/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteNonExistingResource(self):
        """Non existing resource can't be deleted."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteBuiltinResource(self):
        """SeisHub builtin resources can't be deleted."""
        proc = Processor(self.env)
        # fetch a seishub stylesheet
        data = proc.run(GET, '/xml/seishub/stylesheet')
        id = data.keys()[0]
        try:
            proc.run(DELETE, '/xml/seishub/stylesheet/' + id)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteResourceInNonExistingResourceType(self):
        """Resource can't be deleted from non existing resource type."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/notvc2/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteResourceInNonExistingPackage(self):
        """Resource can't be deleted from non existing package."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test2/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteNonExistingNode(self):
        """A non-existing resource node can't be deleted."""
        proc = Processor(self.env)
        try:
            proc.run(DELETE, '/xxx/yyy/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteRevision(self):
        """Revisions may not be deleted via the processor."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/xml/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/xml/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/xml/delete-test/vc/test.xml', StringIO(XML_DOC))
        # with trailing slash
        try:
            proc.run(DELETE, '/xml/delete-test/vc/test.xml/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/xml/delete-test/vc/test.xml')
    
    def test_deleteVersionControlledResource(self):
        """Successful deletion of version controlled resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/xml/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/xml/delete-test/vc/test.xml', StringIO(XML_VCDOC % 1))
        proc.run(POST, '/xml/delete-test/vc/test.xml', StringIO(XML_VCDOC % 2))
        # check latest resource - should be #20
        data = proc.run(GET, '/xml/delete-test/vc/test.xml')
        self.assertEqual(data, XML_VCDOC % 2)
        # check oldest resource -> revision start with 1
        data = proc.run(GET, '/xml/delete-test/vc/test.xml/1')
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/xml/delete-test/vc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.response_code, http.NO_CONTENT)
        # fetch resource again
        try:
            proc.run(GET, '/xml/delete-test/vc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteResource(self):
        """Successful deletion of resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/xml/delete-test/notvc/test.xml', StringIO(XML_DOC))
        # check resource
        data = proc.run(GET, '/xml/delete-test/notvc/test.xml')
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/xml/delete-test/notvc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.response_code, http.NO_CONTENT)
        # delete again
        try:
            proc.run(DELETE, '/xml/delete-test/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # fetch resource again
        try:
            proc.run(GET, '/xml/delete-test/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorDELETETestSuite, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')