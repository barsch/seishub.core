# -*- coding: utf-8 -*-
"""
A test suite for B{GET} request on REST resources.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import registerIndex
from seishub.processor import PUT, POST, DELETE, GET, Processor
from seishub.processor.resources.rest import RESTResource, RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
from sets import Set
from twisted.web import http
import unittest


XML_BASE_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>%s</blahblah1>
    <blah2>%s</blah2>
  </blah1>
</testml>"""

CDATA = """<![CDATA[ &<
>&]]>"""

XML_DOC = XML_BASE_DOC % ("üöäß", "5")
XML_DOC2 = XML_BASE_DOC % ("üöäß", "%d")
XML_DOC3 = XML_BASE_DOC % (CDATA, "5")


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)
    
    package_id = 'get-test'
    resourcetype_id = 'notvc'
    version_control = False
    registerIndex('/testml/blah1/blahblah1', 'text')


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
    registerIndex('/testml/blah1/blah2', 'text')


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
        for _ in xrange(0,5):
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
        """
        Get content of a resource type folder.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # without trailing slash
        data = proc.run(GET, '/get-test/notvc')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/notvc/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a dictionary
        self.assertTrue(isinstance(data, dict))
        # check content
        self.assertTrue(data.has_key('test.xml'))
        # delete resource
        data = proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getVersionControlledResourceTypeFolder(self):
        """
        Get content of a version controlled resource type folder.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 11))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 22))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 33))
        proc.run(PUT, '/get-test/vc/test2.xml', StringIO(XML_DOC2 % 111))
        proc.run(POST, '/get-test/vc/test2.xml', StringIO(XML_DOC2 % 222))
        # without trailing slash
        data = proc.run(GET, '/get-test/vc')
        # with trailing slash
        data2 = proc.run(GET, '/get-test/vc/')
        # both results should equal
        self.assertTrue(Set(data)==Set(data2))
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check content
        self.assertTrue(data.has_key('test.xml'))
        self.assertTrue(data.has_key('test2.xml'))
        # check documents -> must not be a list
        self.assertFalse(isinstance(data['test.xml'].res.document, list))
        self.assertFalse(isinstance(data['test2.xml'].res.document, list))
        # check revisions
        self.assertTrue(data['test.xml'].res.document.revision, 3)
        self.assertTrue(data['test2.xml'].res.document.revision, 2)
        self.assertEquals(data['test.xml'].render_GET(proc), XML_DOC2 % 33)
        self.assertEquals(data['test2.xml'].render_GET(proc), XML_DOC2 % 222)
        # delete resource
        data = proc.run(DELETE, '/get-test/vc/test.xml')
        data = proc.run(DELETE, '/get-test/vc/test2.xml')
    
    def test_getNotExistingResourceType(self):
        proc = Processor(self.env)
        # cycle through some garbage URLs
        path = '/get-test'
        for _ in xrange(0,5):
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
        res1 = proc.run(GET, '/get-test/notvc/test.xml')
        data1 = res1.render(proc)
        # with trailing slash
        res2 = proc.run(GET, '/get-test/notvc/test.xml/')
        data2 = res2.render(proc)
        # res must be RESTResource objects
        self.assertTrue(isinstance(res1, RESTResource))
        self.assertTrue(isinstance(res2, RESTResource))
        # both results should equal
        self.assertTrue(Set(data1)==Set(data2))
        # data must be a basestring
        self.assertTrue(isinstance(data1, basestring))
        # check content
        self.assertTrue(data1, XML_DOC)
        # delete resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getRevision(self):
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC))
        # without trailing slash
        res1 = proc.run(GET, '/get-test/vc/test.xml/1')
        data1 = res1.render_GET(proc)
        # with trailing slash
        res2 = proc.run(GET, '/get-test/vc/test.xml/1/')
        data2 = res2.render_GET(proc)
        # res must be RESTResource objects
        self.assertTrue(isinstance(res1, RESTResource))
        self.assertTrue(isinstance(res2, RESTResource))
        # both results should equal
        self.assertTrue(data1==data2)
        # check content
        self.assertTrue(data1, XML_DOC)
        # GET revision 2
        res3 = proc.run(GET, '/get-test/vc/test.xml/2')
        data3 = res3.render_GET(proc)
        self.assertEquals(data3, XML_DOC)
        res4 = proc.run(GET, '/get-test/vc/test.xml/2/')
        data4 = res4.render_GET(proc)
        self.assertEquals(data4, XML_DOC)
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
        res1 = proc.run(GET, '/get-test/notvc/test.xml/1')
        data1 = res1.render(proc)
        # with trailing slash
        res2 = proc.run(GET, '/get-test/notvc/test.xml/1/')
        data2 = res2.render(proc)
        # res must be RESTResource objects
        self.assertTrue(isinstance(res1, RESTResource))
        self.assertTrue(isinstance(res2, RESTResource))
        # both results should equal
        self.assertTrue(Set(data1)==Set(data2))
        # data must be a basestring
        self.assertTrue(isinstance(data1, basestring))
        # check content
        self.assertTrue(data1, XML_DOC)
        # try to GET revision 2
        try:
            proc.run(GET, '/get-test/notvc/test.xml/2')
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        try:
            proc.run(GET, '/get-test/notvc/test.xml/2/')
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # delete resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_dontHijackResources(self):
        """
        Don't hijack resources from different packages - see #65.
        """
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
        proc.run(PUT, '/get-test/notvc/2', StringIO(XML_DOC))
        res = proc.run(GET, '/get-test/notvc/1')
        data = res.render_GET(proc)
        self.assertTrue(data, XML_DOC)
        proc.run(DELETE, '/get-test/notvc/1')
        proc.run(DELETE, '/get-test/notvc/2')
    
    def test_getResourceIndex(self):
        """
        Tests resource index property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # get index XML w/o trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML w/ trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML on revision 1 w/o trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/1/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # get index XML on revision 1 w/ trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/1/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blahblah1</xpath>" in data)
        self.assertTrue("<value>üöäß</value>" in data)
        # remove resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getRevisionIndex(self):
        """
        Tests revision index property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/vc/test.xml/', StringIO(XML_DOC2 % 12))
        proc.run(POST, '/get-test/vc/test.xml/', StringIO(XML_DOC2 % 234))
        proc.run(POST, '/get-test/vc/test.xml/', StringIO(XML_DOC2 % 3456))
        # get index XML of latest revision w/o trailing slash
        res = proc.run(GET, '/get-test/vc/test.xml/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of revision 3 w/o trailing slash
        res = proc.run(GET, '/get-test/vc/test.xml/3/.index')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of latest revision w/ trailing slash
        res = proc.run(GET, '/get-test/vc/test.xml/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # get index XML of revision 3 w/ trailing slash
        res = proc.run(GET, '/get-test/vc/test.xml/3/.index/')
        data = res.render_GET(proc)
        self.assertTrue("<xpath>/testml/blah1/blah2</xpath>" in data)
        self.assertTrue("<value>3456</value>" in data)
        # remove resource
        proc.run(DELETE, '/get-test/vc/test.xml')
    
    def test_getResourceMetaData(self):
        """
        Tests resource meta data property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC))
        # get meta data XML w/o trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>notvc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # get meta data XML w/ trailing slash
        res = proc.run(GET, '/get-test/notvc/test.xml/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>notvc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # remove resource
        proc.run(DELETE, '/get-test/notvc/test.xml')
    
    def test_getRevisionMetaData(self):
        """
        Tests revision meta data property.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 12))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 234))
        proc.run(POST, '/get-test/vc/test.xml', StringIO(XML_DOC2 % 3456))
        # get meta data XML w/o trailing slash from latest revision
        res = proc.run(GET, '/get-test/vc/test.xml/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>3</revision>' in data)
        # get meta data XML w/ trailing slash from latest revision
        res = proc.run(GET, '/get-test/vc/test.xml/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>3</revision>' in data)
        # get meta data XML w/o trailing slash from 1. revision
        res = proc.run(GET, '/get-test/vc/test.xml/1/.meta')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # get meta data XML w/ trailing slash from 1. revision
        res = proc.run(GET, '/get-test/vc/test.xml/1/.meta/')
        data = res.render_GET(proc)
        self.assertTrue('<package>get-test</package>' in data)
        self.assertTrue('<resourcetype>vc</resourcetype>' in data)
        self.assertTrue('<name>test.xml</name>' in data)
        self.assertTrue('<revision>1</revision>' in data)
        # remove resource
        proc.run(DELETE, '/get-test/vc/test.xml')
    
    def test_withCDATASection(self):
        """
        Upload a XML document with CDATA section.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/get-test/notvc/test.xml', StringIO(XML_DOC3))
        
        res = proc.run(GET, '/get-test/notvc/test.xml/1/.index/')
        data = res.render_GET(proc)
        print data
        # delete resource
        proc.run(DELETE, '/get-test/notvc/test.xml')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestGETTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')