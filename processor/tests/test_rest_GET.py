# -*- coding: utf-8 -*-
"""
A test suite for B{GET} request on REST resources.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import PackageInstaller
from seishub.processor import PUT, POST, DELETE, GET, Processor
from seishub.processor.resources import RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
from sets import Set
from twisted.web import http
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'get-test'
    resourcetype_id = 'notvc'
    version_control = False


class AResourceType2(Component):
    """
    Another test package and resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'get-test2'
    resourcetype_id = 'notvc'
    version_control = False


class AResourceType3(Component):
    """
    Another test package and resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'get-test'
    resourcetype_id = 'notvc2'
    version_control = False


class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'get-test'
    resourcetype_id = 'vc'
    version_control = True


class RestGETTests(SeisHubEnvironmentTestCase):
    """
    A test suite for GET request on REST resources.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_getRoot(self):
        proc = Processor(self.env)
        # without trailing slash
        data = proc.run(GET, '')
        # with trailing slash
        data2 = proc.run(GET, '/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check content
        self.assertTrue(data.has_key('get-test'))
        self.assertTrue(data.has_key('seishub'))
        self.assertFalse(data.has_key('get-test2'))
    
    def test_getPackage(self):
        proc = Processor(self.env)
        # without trailing slash
        data = proc.run(GET, '/get-test')
        # with trailing slash
        data2 = proc.run(GET, '/get-test')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check content
        self.assertTrue(data.has_key('notvc'))
        self.assertTrue(data.has_key('vc'))
    
    def test_getNotExistingPackage(self):
        proc = Processor(self.env)
        # cycle through some garbage URLs
        path = ''
        for _ in range(0,5):
            path = path + '/yyy'
            # without trailing slash
            try:
                proc.run(DELETE, path)
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_FOUND)
            # with trailing slash
            try:
                proc.run(DELETE, path + '/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_getDisabledPackage(self):
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/get-test2')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # with trailing slash
        try:
            proc.run(DELETE, '/get-test2/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_getResourceTypeFolder(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # without trailing slash
        data = proc.run(GET, '/get-test/notvc')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/notvc/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check content
        self.assertTrue(data.has_key('test.xml'))
        # delete resource
        data = proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getNotExistingResourceType(self):
        proc = Processor(self.env)
        # cycle through some garbage URLs
        path = '/get-test'
        for _ in range(0,5):
            path = path + '/yyy'
            # without trailing slash
            try:
                proc.run(DELETE, path)
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_FOUND)
            # with trailing slash
            try:
                proc.run(DELETE, path + '/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_getDisabledResourceType(self):
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/get-test/notvc2')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # with trailing slash
        try:
            proc.run(DELETE, '/get-test/notvc2/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_getResource(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # without trailing slash
        data = proc.run(GET, '/get-test/notvc/test.xml')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/notvc/test.xml/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a basestring
        self.assertTrue(isinstance(data, basestring))
        # check content
        self.assertTrue(data, XML_DOC)
        # delete resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getRevision(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC))
        # without trailing slash
        data = proc.run(GET, '/get-test/vc/test.xml/1')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/vc/test.xml/1/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a basestring
        self.assertTrue(isinstance(data, basestring))
        # check content
        self.assertTrue(data, XML_DOC)
        # GET revision 2
        data = proc.run(GET, '/get-test/vc/test.xml/2')
        self.assertEquals(data, XML_DOC)
        data = proc.run(GET, '/get-test/vc/test.xml/2/')
        self.assertEquals(data, XML_DOC)
        # delete resource
        proc.run(DELETE, '/get-test/vc/test.xml')
    
    def test_getRevisionFromNotVersionControlledResource(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # revision #1 always exist
        # without trailing slash
        data = proc.run(GET, '/get-test/notvc/test.xml/1')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/notvc/test.xml/1/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a basestring
        self.assertTrue(isinstance(data, basestring))
        # check content
        self.assertTrue(data, XML_DOC)
        # try to GET revision 2
        try:
            data = proc.run(GET, '/get-test/notvc/test.xml/2')
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        try:
            data = proc.run(GET, '/get-test/notvc/test.xml/2/')
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # delete resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_dontHijackResources(self):
        """Don't hijack resources from different packages - see #65."""
        # temporary disable resource type 2 and install resource type 1
        self.env.disableComponent(AResourceType2)
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        proc = Processor(self.env)
        proc.run(PUT, '/get-test/notvc/1', StringIO(XML_DOC))
        # disable resource type 1
        self.env.disableComponent(AResourceType)
        # install resource type 2
        self.env.enableComponent(AResourceType2)
        PackageInstaller.install(self.env)
        # try to fetch existing resource from disabled resource type 1
        try:
            proc.run(GET, '/get-test/notvc/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/get-test2/notvc/muh')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/get-test2/notvc/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        self.env.enableComponent(AResourceType)
        proc.run(DELETE, '/get-test/notvc/1')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestGETTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')