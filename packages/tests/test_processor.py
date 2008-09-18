# -*- coding: utf-8 -*-
import unittest
import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, RequestError
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.interfaces import IGETMapper, IPUTMapper, \
                                        IDELETEMapper, IPOSTMapper
from seishub.packages.installer import PackageInstaller


XML_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>
"""

XML_DOC2 = """<?xml version="1.0" encoding="UTF-8"?>
<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
  <hallowelt />
</testml>
"""


class AResourceType(Component):
    implements(IResourceType, IPackage)
    package_id = 'test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    implements(IResourceType, IPackage)
    package_id = 'test'
    resourcetype_id = 'vc'
    version_control = True


class TestMapper(Component):
    implements(IGETMapper, IPUTMapper, IDELETEMapper, IPOSTMapper)
    
    mapping_url = '/test/testmapping'
    
    def processGET(self, request):
        pass
    
    def processPUT(self, request):
        pass

    def processDELETE(self, request):
        pass
    
    def processPOST(self, request):
        pass


class TestMapper2(Component):
    implements(IGETMapper)
    
    mapping_url = '/test2/testmapping'
    
    def processGET(self, request):
        pass


class TestMapper3(Component):
    implements(IGETMapper)
    
    mapping_url = '/test/vc/muh'
    
    def processGET(self, request):
        pass


class ProcessorTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        PackageInstaller.install(self.env)
    
    def test_processRoot(self):
        request = Processor(self.env)
        request.path = '/'
        # test invalid or forbidden methods
        self._test_invalid_methods(request)
        self._test_forbidden_methods(request)
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # should have at least 'package', 'property' and 'mapping' as keys
        self._test_process_result(data, ['package', 'property', 'mapping'])
        # check entries in packages
        self.assertTrue('/test' in data.get('package'))
        self.assertTrue('/seishub' in data.get('package'))
        # check entries in mapping
        self.assertTrue('/test2' in data.get('mapping'))
        self.assertFalse('/test' in data.get('mapping'))
    
    def test_processPackage(self):
        request = Processor(self.env)
        request.path = '/test'
        # test invalid or forbidden methods
        self._test_invalid_methods(request)
        self._test_forbidden_methods(request)
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # should have 'resourcetype', 'alias', 'property' and 'mapping'
        self._test_process_result(data, ['resourcetype', 'alias', 'property', 
                                         'mapping'])
        # check entries in resourcetypes
        self.assertTrue('/test/vc' in data.get('resourcetype'))
        self.assertTrue('/test/notvc' in data.get('resourcetype'))
        # check entries in mapping
        self.assertTrue('/test/testmapping' in data.get('mapping'))
        self.assertFalse('/test2/testmapping' in data.get('mapping'))
        self.assertFalse('/test/vc' in data.get('mapping'))
    
    def test_processPackageAlias(self):
        pass
    
    def test_processResourceType(self):
        request = Processor(self.env)
        request.path = '/test/notvc'
        # test invalid or forbidden methods
        self._test_invalid_methods(request)
        self._test_forbidden_methods(request, ['POST', 'DELETE'])
        # test valid GET method
        request.method = 'GET'
        data = request.process()
        # should have at least 'index', 'alias', 'mapping' and 'property'
        self._test_process_result(data, ['index', 'alias', 'mapping', 
                                         'property', 'resource'])
        # test valid PUT method
        request.method = 'PUT'
        request.content = StringIO.StringIO(XML_DOC)
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.CREATED)
        self.assertTrue(isinstance(request.response_header, dict))
        response_header = request.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(request.path))
        # fetch all resources via property .all
        request.method = 'GET'
        request.path = '/test/notvc'
        data = request.process()
        # only resources should be there
        self.assertTrue(data.has_key('resource'))
        self.assertTrue(isinstance(data.get('resource'),list))
        self.assertTrue(location in data.get('resource'))
        # fetch resource and compare it with original
        request.path = location
        data = request.process()
        self.assertTrue(data, XML_DOC)
        # delete uploaded resource
        request.method = 'DELETE'
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.NO_CONTENT)
    
    def test_processResourceTypeAlias(self):
        pass
    
    def test_processResource(self):
        request = Processor(self.env)
        # DELETE resource
        request.method = 'DELETE'
        # id is no integer
        request.path = '/test/notvc/idisnointeger'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.FORBIDDEN)
        # package and/or resource type does not exists
        request.path = '/xxx/yyy/1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.FORBIDDEN)
        # id does not exists
        request.path = '/test/notvc/-1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.INTERNAL_SERVER_ERROR)
        # upload a resource via PUT
        request.path = '/test/notvc'
        request.method = 'PUT'
        request.content = StringIO.StringIO(XML_DOC)
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.CREATED)
        self.assertTrue(isinstance(request.response_header, dict))
        response_header = request.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(request.path))
        # GET resource
        request.method = 'GET'
        request.path = location
        data = request.process()
        self.assertEquals(data, XML_DOC)
        # overwrite this resource via POST request
        request.path = location
        request.method = 'POST'
        request.content = StringIO.StringIO(XML_DOC2)
        data = request.process()
        # GET resource
        request.method = 'GET'
        request.path = location
        data = request.process()
        self.assertNotEquals(data, XML_DOC)
        self.assertEquals(data, XML_DOC2)
        # DELETE resource
        request.method = 'DELETE'
        request.path = location
        request.process()
        # GET deleted revision
        request.method = 'GET'
        request.path = location
        try:
            data = request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.NOT_FOUND)
    
    def test_processVersionControlledResource(self):
        request = Processor(self.env)
        request.path = '/test/vc'
        # upload a resource via PUT
        request.method = 'PUT'
        request.content = StringIO.StringIO(XML_DOC)
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.CREATED)
        self.assertTrue(isinstance(request.response_header, dict))
        response_header = request.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(request.path))
        # overwrite this resource via POST request
        request.path = location
        request.method = 'POST'
        request.content = StringIO.StringIO(XML_DOC2)
        data = request.process()
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(request.response_code, http.NO_CONTENT)
        self.assertTrue(isinstance(request.response_header, dict))
        response_header = request.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(request.path))
        # GET latest revision
        request.method = 'GET'
        data = request.process()
        self.assertEquals(data, XML_DOC2)
        # GET revision #1
        request.method = 'GET'
        request.path = location+'/1'
        data = request.process()
        self.assertEquals(data, XML_DOC)
        # GET revision #2
        request.method = 'GET'
        request.path = location+'/2'
        data = request.process()
        self.assertEquals(data, XML_DOC2)
        # GET revision #3 -> does not exists
        request.method = 'GET'
        request.path = location+'/3'
        try:
            data = request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.NOT_FOUND)
        # DELETE resource
        request.method = 'DELETE'
        request.path = location
        request.process()
        # GET deleted revision
        request.method = 'GET'
        request.path = location
        try:
            data = request.process()
        except Exception, e:
            assert isinstance(e, RequestError)
            self.assertEqual(e.message, http.GONE)
    
    def _test_invalid_methods(self, request, 
                              methods=['HEAD', 'XXX', 'GETPUT']):
        # test invalid methods
        for method in methods:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.NOT_ALLOWED)
    
    def _test_forbidden_methods(self, request, 
                                methods=['POST', 'PUT', 'DELETE']):
        # test forbidden methods
        for method in methods:
            request.method = method
            try:
                request.process()
            except Exception, e:
                assert isinstance(e, RequestError)
                self.assertEqual(e.message, http.FORBIDDEN)
    
    def _test_process_result(self, data, fields=[]):
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # test for fields
        for field in fields:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')