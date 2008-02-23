# -*- coding: utf-8 -*-

import unittest
from twisted.enterprise import util as dbutil

from sqlalchemy.sql import and_

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalogError, \
                                          InvalidIndexError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.defaults import *
from seishub.xmldb.xpath import XPathQuery


RAW_XML1="""<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
</station>"""

RAW_XML2 = """<station rel_uri="genf">
    <station_code>GENF</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>22.51200</lon>
    <lat>55.23200</lat>
    <stat_elav>0.73500</stat_elav>
    <XY>
        <paramXY>2.5</paramXY>
        <paramXY>0</paramXY>
        <paramXY>99</paramXY>
    </XY>
</station>"""

RAW_XML3 = """<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""

URI1 = "/real/bern"
URI2 = "/fake/genf"
URI3 = "/testml/res1"

IDX1 = "/station/lon"
IDX2 = "/station/lat"
IDX3 = "/testml/blah1/@id"
IDX4 = "/station/XY/paramXY"

class XmlIndexCatalogTest(SeisHubTestCase):
    #TODO: testGetIndexes
    _last_id=0
    _test_kp="XY/paramXY"
    _test_vp="/station"
    _test_uri="/stations/bern"
        
    def __init__(self, *args, **kwargs):
        super(XmlIndexCatalogTest,self).__init__(*args,**kwargs)
        self.catalog = self.env.catalog.index_catalog
    
    def _setup_testdata(self):
        # create us a small test catalog
        res1=self.env.catalog.newXmlResource(URI1,RAW_XML1)
        res2=self.env.catalog.newXmlResource(URI2,RAW_XML2)
        res3=self.env.catalog.newXmlResource(URI3,RAW_XML3)
        idx1=self.env.catalog.newXmlIndex(IDX1)
        idx2=self.env.catalog.newXmlIndex(IDX2)
        idx3=self.env.catalog.newXmlIndex(IDX3)
        idx4=self.env.catalog.newXmlIndex(IDX4)
        self.env.catalog.addResource(res1)
        self.env.catalog.addResource(res2)
        self.env.catalog.addResource(res3)
        self.env.catalog.registerIndex(idx1)
        self.env.catalog.registerIndex(idx2)
        self.env.catalog.registerIndex(idx3)
        self.env.catalog.registerIndex(idx4)
        self.env.catalog.reindex(IDX1)
        self.env.catalog.reindex(IDX2)
        self.env.catalog.reindex(IDX3)
        self.env.catalog.reindex(IDX4)
        
    def _cleanup_testdata(self):
        self.env.catalog.removeIndex(IDX1)
        self.env.catalog.removeIndex(IDX2)
        self.env.catalog.removeIndex(IDX3)
        self.env.catalog.removeIndex(IDX4)
        self.env.catalog.deleteResource(URI1)
        self.env.catalog.deleteResource(URI2)
        self.env.catalog.deleteResource(URI3)
    
    def _assertClassAttributesEqual(self,first,second):
        return self.assertEquals(first.__dict__,second.__dict__)
    
    def _assertClassCommonAttributesEqual(self,first,second):
        # compare two classes' common attributes
        f=dict(first.__dict__)
        s=dict(second.__dict__)
        for k in s:
            if k not in f:
                f[k]=s[k]
        for k in f:
            if k not in s:
                s[k]=f[k]
        return self.assertEquals(f,s)
    
    def __cleanUp(self,res=None):
        # manually remove some db entries created
        query = index_def_tab.delete(and_(
                                     index_def_tab.c.key_path==self._test_kp,
                                     index_def_tab.c.value_path==self._test_vp)
                )
        self.db.engine.execute(query)
    
    def testRegisterIndex(self):
        test_kp=self._test_kp
        test_vp=self._test_vp
        catalog=XmlIndexCatalog(self.db)
        test_index=XmlIndex(key_path=test_kp,
                            value_path=test_vp)
        catalog.registerIndex(test_index)
        
        str_map={'prefix':DEFAULT_PREFIX,
                 'table':INDEX_DEF_TABLE,
                 'key_path':dbutil.quote(test_kp,"text"),
                 'value_path':dbutil.quote(test_vp,"text")}
        query=("SELECT key_path,value_path FROM %(prefix)s%(table)s " + \
                "WHERE (key_path=%(key_path)s AND value_path=%(value_path)s)") \
                % (str_map)
                
        res = self.db.engine.execute(query).fetchall()
        self.assertEquals(res[0][0],self._test_kp)
        self.assertEquals(res[0][1],self._test_vp)
        
        # try to add a duplicate:
        self.assertRaises(XmlIndexCatalogError,catalog.registerIndex,test_index)
        
        # clean up:
        self.__cleanUp()
    
    def testRemoveIndex(self):
        # first register an index to be removed:
        catalog = XmlIndexCatalog(self.db)
        test_index = XmlIndex(key_path = self._test_kp,
                              value_path = self._test_vp)
        catalog.registerIndex(test_index)
        
        # ... and remove again:
        r = catalog.removeIndex(key_path=self._test_kp,
                                value_path=self._test_vp)
        self.assertTrue(r)
    
    def testGetIndex(self):
        # first register an index to grab, and retrieve it's id:
        catalog=XmlIndexCatalog(db=self.db)
        test_index=XmlIndex(key_path=self._test_kp,value_path=self._test_vp)
        catalog.registerIndex(test_index)
        
        #TODO: invalid index should raise exception
                
        # get by key:
        res = catalog.getIndex(key_path = self._test_kp,
                         value_path = self._test_vp)
        self._assertClassCommonAttributesEqual(test_index, res)
        
        # remove:
        catalog.removeIndex(key_path=self._test_kp,
                            value_path=self._test_vp)
    
    def testIndexResource(self):
        dbmgr = XmlDbManager(self.db)
        catalog = XmlIndexCatalog(db = self.db,
                                  resource_storage = dbmgr)
        bad_catalog = XmlIndexCatalog(db = self.db)
        
        # register a test resource:
        test_res=XmlResource(uri = self._test_uri, xml_data = RAW_XML1)
        try:
            dbmgr.addResource(test_res)
        except:
            print "Resource is already present in db."

        # register a test index:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp)
        catalog.registerIndex(test_index)
        
        # index test resource:
        catalog.indexResource(self._test_uri, 
                              test_index.getValue_path(), 
                              test_index.getKey_path())
        
        # without storage:
        self.assertRaises(XmlIndexCatalogError,bad_catalog.indexResource,
                          self._test_uri, 
                          test_index.getValue_path(), test_index.getKey_path())
        
        #TODO: check db entries made
                
        # pass invalid index args:
        self.assertRaises(InvalidIndexError, catalog.indexResource,
                          self._test_uri, value_path="blub", key_path="blah")
        
        # clean up:
        catalog.removeIndex(key_path=self._test_kp, value_path=self._test_vp)
        dbmgr.deleteResource(self._test_uri)
    
    def testFlushIndex(self):
        dbmgr=XmlDbManager(self.db)
        catalog=XmlIndexCatalog(self.db,dbmgr)
        #first register an index and add some data:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp)
        try:
            catalog.registerIndex(test_index)
        except:
            print "Index is already present in db."
        
        test_res = XmlResource(uri = self._test_uri, xml_data = RAW_XML1)
        try:
            dbmgr.addResource(test_res)
        except:
            raise
            print "Resource is already present in db."
        
        catalog.indexResource(test_res.getUri(), test_index.getValue_path(),
                              test_index.getKey_path())
        #flush index:
        catalog.flushIndex(value_path=self._test_vp, 
                           key_path=self._test_kp)
        
        #TODO: check if index is properly flushed
        
        # clean up:
        catalog.removeIndex(test_index.getValue_path(), test_index.getKey_path())
        dbmgr.deleteResource(self._test_uri)
        
    def testQuery(self):
        # create test catalog
        try:
            self._setup_testdata()
        except:
            print "Test catalog might already be present in db."
        
        q0 = "/station[lon != 12.51200 and lat = 55.23200]"
        q1 = "/station[lat]"
        q2 = "/station[XY/paramXY or lon = 12.51200]"
        q3 = "/testml"

        res0 = self.catalog.query(XPathQuery(q0))
        res1 = self.catalog.query(XPathQuery(q1))
        res2 = self.catalog.query(XPathQuery(q2))
        res3 = self.catalog.query(XPathQuery(q3))
        
        self.assertEqual(res0.sort(), [URI2].sort())
        self.assertEqual(res1.sort(), [URI1, URI2].sort())
        self.assertEqual(res2.sort(), [URI1, URI2].sort())
        self.assertEqual(res3.sort(), [URI3].sort())
                
        # remove test catalog
        self._cleanup_testdata()

def suite():
    return unittest.makeSuite(XmlIndexCatalogTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')