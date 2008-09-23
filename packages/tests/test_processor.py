# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
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

XML_VC_DOC = """<?xml version="1.0" encoding="UTF-8"?>
<testml>%d</testml>
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
        proc = Processor(self.env)
        proc.path = '/'
        # test invalid or forbidden methods
        self._test_invalid_methods(proc)
        self._test_forbidden_methods(proc)
        # test valid GET method
        data = proc.run('GET', '/')
        # should have at least 'package', 'property' and 'mapping' as keys
        self._test_process_result(data, ['package', 'property', 'mapping'])
        # check entries in packages
        self.assertTrue('/test' in data.get('package'))
        self.assertTrue('/seishub' in data.get('package'))
        # check entries in mapping
        self.assertTrue('/test2' in data.get('mapping'))
        self.assertFalse('/test' in data.get('mapping'))
    
    def test_processPackage(self):
        proc = Processor(self.env)
        proc.path = '/test'
        # test invalid or forbidden methods
        self._test_invalid_methods(proc)
        self._test_forbidden_methods(proc)
        # test valid GET method
        data = proc.run('GET', '/test')
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
        proc = Processor(self.env)
        proc.path = '/test/notvc'
        # test invalid or forbidden methods
        self._test_invalid_methods(proc)
        self._test_forbidden_methods(proc, ['POST', 'DELETE'])
        # test valid GET method
        data = proc.run('GET', '/test/notvc')
        # should have at least 'index', 'alias', 'mapping' and 'property'
        self._test_process_result(data, ['index', 'alias', 'mapping', 
                                         'property', 'resource'])
        # test valid PUT method
        data = proc.run('PUT', '/test/notvc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.CREATED)
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(proc.path))
        # fetch all resources via property .all
        data = proc.run('GET', '/test/notvc')
        # only resources should be there
        self.assertTrue(data.has_key('resource'))
        self.assertTrue(isinstance(data.get('resource'),list))
        self.assertTrue(location in data.get('resource'))
        # fetch resource and compare it with original
        data = proc.run('GET', location)
        self.assertTrue(data, XML_DOC)
        # delete uploaded resource
        data = proc.run('DELETE', location)
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.NO_CONTENT)
    
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
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.BAD_REQUEST)
        # package and/or resource type does not exists
        request.path = '/xxx/yyy/1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.FORBIDDEN)
        # id does not exists
        request.path = '/test/notvc/-1'
        try:
            request.process()
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.INTERNAL_SERVER_ERROR)
        # upload a resource via PUT
        request.path = '/test/notvc'
        request.method = 'PUT'
        request.content = StringIO(XML_DOC)
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
        request.content = StringIO(XML_DOC2)
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
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_processVCResource(self):
        """Test for a version controlled resource."""
        request = Processor(self.env)
        request.path = '/test/vc'
        # upload a resource via PUT
        request.method = 'PUT'
        request.content = StringIO(XML_DOC)
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
        request.content = StringIO(XML_DOC2)
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
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
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
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.GONE)
    
    def test_processVCResourceDeletion(self):
        """Test for deletion behavior of version controlled resources."""
        proc = Processor(self.env)
        proc.run('PUT', '/test/vc', StringIO(XML_VC_DOC % 1000)) 
        # upload a test resources via PUT
        loc = proc.response_header.get('Location')
        # modify both resources a few times
        for i in range(20):
            data = proc.run('POST', loc, StringIO(XML_VC_DOC % i)) 
            # check response; data should be empty; we look into request
            self.assertFalse(data)
            self.assertEqual(proc.response_code, http.NO_CONTENT)
            self.assertTrue(isinstance(proc.response_header, dict))
            response_header = proc.response_header
            self.assertTrue(response_header.has_key('Location'))
            self.assertEqual(loc, response_header.get('Location'))
        # check latest resource
        print loc
        data = proc.run('GET', loc)
        print data
        self.assertEqual(data, XML_VC_DOC % 19)
        # check oldest resource -> revision start with 1
        proc.method = 'GET'
        proc.path = loc + '/1'
        data = proc.process()
        self.assertEqual(data, XML_VC_DOC % 1000)
        # check all other revisions
        proc.method = 'GET'
        for i in range(20):
            proc.path = loc + '/' + str(i+2)
            data = proc.process()
            self.assertEqual(data, XML_VC_DOC % i)
        # delete latest revision
        proc.method = 'DELETE'
        proc.path = loc + '/20'
        proc.process()
        # check latest resource
        proc.method = 'GET'
        proc.path = loc
        data = proc.process()
        self.assertEqual(data, XML_VC_DOC % 18)
        
    
    def _test_invalid_methods(self, proc, methods=['HEAD', 'XXX', 'GETPUT']):
        # test invalid methods
        for method in methods:
            proc.method = method
            try:
                proc.process()
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.NOT_ALLOWED)
    
    def _test_forbidden_methods(self, proc, methods=['POST', 'PUT', 'DELETE']):
        # test forbidden methods
        for method in methods:
            proc.method = method
            try:
                proc.process()
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.FORBIDDEN)
    
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