# -*- coding: utf-8 -*-
"""
A general test suite for REST resources.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor import PUT, POST, DELETE, MOVE, Processor
from seishub.processor.resources import RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


NOT_IMPLEMENTED_HTTP_METHODS = ['TRACE', 'COPY', 'PROPFIND','PROPPATCH', 
                                'MKCOL', 'CONNECT', 'PATCH', 'LOCK', 'UNLOCK']

XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""

XML_VC_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'rest-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'rest-test'
    resourcetype_id = 'vc'
    version_control = True


class RestTests(SeisHubEnvironmentTestCase):
    """
    A general test suite for REST resources.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_notImplementedMethodsOnRoot(self):
        proc = Processor(self.env)
        for method in NOT_IMPLEMENTED_HTTP_METHODS:
            # without trailing slash
            try:
                proc.run(method, '')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
            # with trailing slash
            try:
                proc.run(method, '/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
    
    def test_notImplementedMethodsOnPackage(self):
        proc = Processor(self.env)
        for method in NOT_IMPLEMENTED_HTTP_METHODS:
            # without trailing slash
            try:
                proc.run(method, '/rest-test')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
    
    def test_notImplementedMethodsOnResourceType(self):
        proc = Processor(self.env)
        for method in NOT_IMPLEMENTED_HTTP_METHODS:
            # without trailing slash
            try:
                proc.run(method, '/rest-test/notvc')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/notvc/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
    
    def test_notImplementedMethodsOnResource(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/rest-test/notvc/test.xml', StringIO(XML_DOC))
        for method in NOT_IMPLEMENTED_HTTP_METHODS:
            # without trailing slash
            try:
                proc.run(method, '/rest-test/notvc')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/notvc/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
        # delete resource
        proc.run(DELETE, '/rest-test/notvc/test.xml')
    
    def test_notImplementedMethodsOnRevision(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        for method in NOT_IMPLEMENTED_HTTP_METHODS:
            # without trailing slash
            try:
                proc.run(method, '/rest-test/vc/2')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/vc/2/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_IMPLEMENTED)
        # delete resource
        proc.run(DELETE, '/rest-test/vc/test.xml')
    
    def test_forbiddenMethodsOnRoot(self):
        proc = Processor(self.env)
        for method in [POST, PUT, DELETE, MOVE]:
            # without trailing slash
            try:
                proc.run(method, '')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
            # with trailing slash
            try:
                proc.run(method, '/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
    
    def test_forbiddenMethodsOnPackage(self):
        proc = Processor(self.env)
        for method in [POST, PUT, DELETE, MOVE]:
            # without trailing slash
            try:
                proc.run(method, '/rest-test')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
    
    def test_forbiddenMethodsOnResourceType(self):
        proc = Processor(self.env)
        for method in [POST, DELETE, MOVE]:
            # without trailing slash
            try:
                proc.run(method, '/rest-test/notvc')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/notvc/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
    
    def test_forbiddenMethodsOnRevision(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        for method in [DELETE, MOVE, POST, PUT]:
            # without trailing slash
            try:
                proc.run(method, '/rest-test/vc/test.xml/2')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
            # with trailing slash
            try:
                proc.run(method, '/rest-test/vc/test.xml/2/')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.NOT_ALLOWED)
        # delete resource
        proc.run(DELETE, '/rest-test/vc/test.xml')
    
    def test_orderOfAddingResourcesMatters(self):
        """
        This test in this specific order failed in a previous revision.
        """ 
        proc = Processor(self.env)
        proc.run(PUT, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/rest-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/rest-test/notvc/test.xml', StringIO(XML_DOC))
        proc.run(DELETE, '/rest-test/vc/test.xml')
        proc.run(DELETE, '/rest-test/notvc/test.xml')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')