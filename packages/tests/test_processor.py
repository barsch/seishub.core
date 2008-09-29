# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET
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
    """A non versioned test resource type."""
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


class TestMapper(Component):
    """A test mapper."""
    implements(IGETMapper, IPUTMapper, IDELETEMapper, IPOSTMapper)
    
    package_id = 'test'
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
    """Another test mapper."""
    implements(IGETMapper)
    
    package_id = 'test'
    mapping_url = '/test2/testmapping'
    
    def processGET(self, request):
        pass


class TestMapper3(Component):
    """And one more test mapper."""
    implements(IGETMapper)
    
    mapping_url = '/test/vc/muh'
    
    def processGET(self, request):
        pass


class ProcessorTest(SeisHubEnvironmentTestCase):
    """Processor test case."""
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        PackageInstaller.install(self.env)
        
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
        self.env.disableComponent(TestMapper)
        self.env.disableComponent(TestMapper2)
    
    def test_processRoot(self):
        proc = Processor(self.env)
        # test forbidden methods
        for method in [POST, PUT, DELETE]:
            try:
                proc.run(method, '/')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.FORBIDDEN)
        # test invalid methods
        for method in ['HEAD', 'XXX', 'GETPUT']:
            try:
                proc.run(method, '/')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.NOT_ALLOWED)
        # test valid GET method
        data = proc.run(GET, '/')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # should have at least 'package', 'property' and 'mapping' as keys
        for field in ['package', 'property', 'mapping']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
        # check entries in packages
        self.assertTrue('/test' in data.get('package'))
        self.assertTrue('/seishub' in data.get('package'))
        # check entries in mapping
        self.assertTrue('/test2' in data.get('mapping'))
        self.assertFalse('/test' in data.get('mapping'))
    
    def test_processPackage(self):
        proc = Processor(self.env)
        # test forbidden methods
        for method in [POST, PUT, DELETE]:
            try:
                proc.run(method, '/test')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.FORBIDDEN)
        # test invalid methods
        for method in ['HEAD', 'XXX', 'GETPUT']:
            try:
                proc.run(method, '/test')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.NOT_ALLOWED)
        # test valid GET method
        data = proc.run(GET, '/test')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # should have 'resourcetype', 'alias', 'property' and 'mapping'
        for field in ['resourcetype', 'alias', 'property', 'mapping']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
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
        # test forbidden methods
        for method in [POST, DELETE]:
            try:
                proc.run(method, '/')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.FORBIDDEN)
        # test invalid methods
        for method in ['HEAD', 'XXX', 'GETPUT']:
            try:
                proc.run(method, '/')
            except Exception, e:
                assert isinstance(e, ProcessorError)
                self.assertEqual(e.code, http.NOT_ALLOWED)
        # test valid GET method
        data = proc.run(GET, '/test/notvc')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # should have at least 'package', 'property' and 'mapping' as keys
        for field in ['index', 'alias', 'mapping', 'property', 'resource']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
        # test valid PUT method
        data = proc.run(PUT, '/test/notvc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.CREATED)
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(proc.path))
        # fetch all resources via property .all
        data = proc.run(GET, '/test/notvc')
        # only resources should be there
        self.assertTrue(data.has_key('resource'))
        self.assertTrue(isinstance(data.get('resource'),list))
        self.assertTrue(location in data.get('resource'))
        # fetch resource and compare it with original
        data = proc.run(GET, location)
        self.assertTrue(data, XML_DOC)
        # delete uploaded resource
        data = proc.run(DELETE, location)
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.NO_CONTENT)
    
    def test_processResourceTypeAlias(self):
        pass
    
    def test_processResource(self):
        proc = Processor(self.env)
        # DELETE resource
        # package and/or resource type does not exists
        try:
            proc.run(DELETE, '/xxx/yyy/1')
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.FORBIDDEN)
        # id does not exists
        try:
            proc.run(DELETE, '/test/notvc/-1')
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
        # upload a resource via PUT
        data = proc.run(PUT, '/test/notvc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.CREATED)
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(proc.path))
        # GET resource
        data = proc.run(GET, location)
        self.assertEquals(data, XML_DOC)
        # overwrite this resource via POST request
        proc.run(POST, location, StringIO(XML_DOC2))
        # GET resource
        data = proc.run(GET, location)
        self.assertNotEquals(data, XML_DOC)
        self.assertEquals(data, XML_DOC2)
        # DELETE resource
        proc.run(DELETE, location)
        # GET deleted revision
        try:
            proc.run(GET, location)
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_processVCResource(self):
        """Test for a version controlled resource."""
        proc = Processor(self.env)
        # upload a resource via PUT
        data = proc.run(PUT, '/test/vc', StringIO(XML_DOC))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.CREATED)
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(proc.path))
        # overwrite this resource via POST request
        data = proc.run(POST, location, StringIO(XML_DOC2))
        # check response; data should be empty; we look into request
        self.assertFalse(data)
        self.assertEqual(proc.response_code, http.NO_CONTENT)
        self.assertTrue(isinstance(proc.response_header, dict))
        response_header = proc.response_header
        self.assertTrue(response_header.has_key('Location'))
        location = response_header.get('Location')
        self.assertTrue(location.startswith(proc.path))
        # GET latest revision
        data = proc.run(GET, location)
        self.assertEquals(data, XML_DOC2)
        # GET revision #1
        data = proc.run(GET, location + '/1')
        self.assertEquals(data, XML_DOC)
        # GET revision #2
        data = proc.run(GET, location + '/2')
        self.assertEquals(data, XML_DOC2)
        # GET not existing revision #3
        try:
            data = proc.run(GET, location + '/3')
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
        # DELETE resource
        proc.run(DELETE, location)
        # try to GET deleted revision
        try:
            proc.run(GET, location)
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.GONE)
    
    def test_processVCResourceDeletion(self):
        """Test for deletion behavior of version controlled resources."""
        proc = Processor(self.env)
        proc.run(PUT, '/test/vc', StringIO(XML_VC_DOC % 1000)) 
        # upload a test resources via PUT == version #1
        loc = proc.response_header.get('Location')
        # modify resource a few times
        for i in range(2, 21):
            data = proc.run(POST, loc, StringIO(XML_VC_DOC % i)) 
            # check response; data should be empty; we look into request
            self.assertFalse(data)
            self.assertEqual(proc.response_code, http.NO_CONTENT)
            self.assertTrue(isinstance(proc.response_header, dict))
            response_header = proc.response_header
            self.assertTrue(response_header.has_key('Location'))
            self.assertEqual(loc, response_header.get('Location'))
        # try to modify a revision
        try:
            proc.run(POST, loc + '/4', StringIO(XML_VC_DOC % 4000))
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.FORBIDDEN)
        # check latest resource - should be #20
        data = proc.run(GET, loc)
        self.assertEqual(data, XML_VC_DOC % 20)
        # check oldest resource -> revision start with 1
        data = proc.run(GET, loc + '/1')
        self.assertEqual(data, XML_VC_DOC % 1000)
        # check all other revisions
        for i in range(2, 21):
            data = proc.run(GET, loc + '/' + str(i))
            self.assertEqual(data, XML_VC_DOC % i)
        # delete latest revision
        proc.run(DELETE, loc + '/20')
        # try to delete again
        try:
            proc.run(DELETE, loc + '/20')
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.NOT_FOUND)
        # check latest resource - should be revision #19
        data = proc.run(GET, loc)
        self.assertEqual(data, XML_VC_DOC % 19)
        # delete two revisions in between
        proc.run(DELETE, loc + '/18')
        proc.run(DELETE, loc + '/19')
        # check latest resource - should be revision #17
        data = proc.run(GET, loc)
        self.assertEqual(data, XML_VC_DOC % 17)
        # delete the whole resource
        proc.run(DELETE, loc)
        # try to fetch resource
        try:
            proc.run(GET, loc)
        except Exception, e:
            assert isinstance(e, ProcessorError)
            self.assertEqual(e.code, http.GONE)
        # upload again
        proc.run(PUT, '/test/vc', StringIO(XML_VC_DOC % 2000))
        # XXX: BUG
        proc.run(GET, loc)
        # import pdb;pdb.set_trace()
        # XXX: how to get all revisions


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')