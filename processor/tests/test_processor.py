# -*- coding: utf-8 -*-
"""
A test suite for the Processor.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor import MAXIMAL_URL_LENGTH, ALLOWED_HTTP_METHODS, PUT, \
    POST, DELETE, GET, Processor
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


NOT_IMPLEMENTED_HTTP_METHODS = ['TRACE', 'OPTIONS', 'COPY', 'HEAD', 'PROPFIND',
                                'PROPPATCH', 'MKCOL', 'CONNECT', 'PATCH',
                                'LOCK', 'UNLOCK']

XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""

XML_DOC2 = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
  <hallowelt />
</testml>"""

XML_VC_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'processor-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'processor-test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorTests(SeisHubEnvironmentTestCase):
    """
    A test suite for the Processor.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
    
    def tearDown(self):
        self.env.registry.db_deleteResourceType('processor-test', 'vc')
        self.env.registry.db_deleteResourceType('processor-test', 'notvc')
        self.env.registry.db_deletePackage('processor-test')
    
    def test_oversizedURL(self):
        """
        Request URL is restricted by MAXIMAL_URL_LENGTH.
        """
        proc = Processor(self.env)
        for method in ALLOWED_HTTP_METHODS:
            try:
                proc.run(method, 'a' * MAXIMAL_URL_LENGTH, '')
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.REQUEST_URI_TOO_LONG)
    
    def test_processResourceType(self):
        proc = Processor(self.env)
        proc.path = '/xml/processor-test/notvc'
        # test valid GET method
        data = proc.run(GET, '/xml/processor-test/notvc')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # test valid PUT method
        data = proc.run(PUT, '/xml/processor-test/notvc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.code, http.CREATED)
        self.assertTrue(isinstance(proc.headers, dict))
        self.assertTrue(proc.headers.has_key('Location'))
        location = proc.headers.get('Location')
        self.assertTrue(location.startswith(self.env.getRestUrl() + proc.path))
        # strip REST url from location
        location = location[len(self.env.getRestUrl()):]
        # fetch resource and compare it with original
        data = proc.run(GET, location)
        self.assertTrue(data, XML_DOC)
        # delete uploaded resource
        data = proc.run(DELETE, location)
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.code, http.NO_CONTENT)
    
    def test_processResource(self):
        proc = Processor(self.env)
        # upload a resource via PUT
        data = proc.run(PUT, '/xml/processor-test/notvc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.code, http.CREATED)
        self.assertTrue(isinstance(proc.headers, dict))
        self.assertTrue(proc.headers.has_key('Location'))
        location = proc.headers.get('Location')
        self.assertTrue(location.startswith(self.env.getRestUrl() + proc.path))
        # GET resource
        location = location[len(self.env.getRestUrl()):]
        data = proc.run(GET, location).render_GET(proc)
        self.assertEquals(data, XML_DOC)
        # overwrite this resource via POST request
        proc.run(POST, location, StringIO(XML_DOC2))
        # GET resource
        data = proc.run(GET, location).render_GET(proc)
        self.assertNotEquals(data, XML_DOC)
        self.assertEquals(data, XML_DOC2)
        # DELETE resource
        proc.run(DELETE, location)
        # GET deleted revision
        try:
            proc.run(GET, location).render_GET(proc)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_processVCResource(self):
        """
        Test for a version controlled resource.
        """
        proc = Processor(self.env)
        # upload a resource via PUT
        data = proc.run(PUT, '/xml/processor-test/vc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.code, http.CREATED)
        self.assertTrue(isinstance(proc.headers, dict))
        self.assertTrue(proc.headers.has_key('Location'))
        location = proc.headers.get('Location')
        self.assertTrue(location.startswith(self.env.getRestUrl() + proc.path))
        # overwrite this resource via POST request
        location = location[len(self.env.getRestUrl()):]
        data = proc.run(POST, location, StringIO(XML_DOC2))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.code, http.NO_CONTENT)
        self.assertTrue(isinstance(proc.headers, dict))
        self.assertTrue(proc.headers.has_key('Location'))
        location = proc.headers.get('Location')
        self.assertTrue(location.startswith(self.env.getRestUrl() + proc.path))
        # GET latest revision
        location = location[len(self.env.getRestUrl()):]
        data = proc.run(GET, location).render_GET(proc)
        self.assertEquals(data, XML_DOC2)
        # GET revision #1
        data = proc.run(GET, location + '/1').render_GET(proc)
        self.assertEquals(data, XML_DOC)
        # GET revision #2
        data = proc.run(GET, location + '/2').render_GET(proc)
        self.assertEquals(data, XML_DOC2)
        # GET not existing revision #3
        try:
            data = proc.run(GET, location + '/3').render_GET(proc)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # DELETE resource
        proc.run(DELETE, location)
        # try to GET deleted revision
        try:
            proc.run(GET, location).render_GET(proc)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_strangeRequestPatterns(self):
        """
        Test strange request patterns.
        """
        proc = Processor(self.env)
        # root
        data=proc.run(GET, '///')
        self.assertTrue('xml' in data)
        data=proc.run(GET, '//./')
        self.assertTrue('xml' in data)
        # results in /xml
        data=proc.run(GET, '/xml//')
        self.assertTrue('seishub' in data)
        data=proc.run(GET, '//xml/')
        self.assertTrue('seishub' in data)
        data=proc.run(GET, '//////////////////////xml//////////////')
        self.assertTrue('seishub' in data)
        data=proc.run(GET, '/////////./////////////xml///////.////.///')
        self.assertTrue('seishub' in data)
        # results in /xml/seishub
        data=proc.run(GET, '//////////////////////xml/////////////seishub/')
        self.assertTrue('schema' in data)
        data=proc.run(GET, '/////////////////xml///////.//////seishub////')
        self.assertTrue('schema' in data)
        data=proc.run(GET, '/////////////////xml/../xml////seishub////')
        self.assertTrue('schema' in data)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')