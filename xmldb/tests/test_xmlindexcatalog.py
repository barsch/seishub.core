# -*- coding: utf-8 -*-

import unittest
import os
import inspect

from sqlalchemy.sql import and_

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog, QueryAliases
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalogError, \
                                          InvalidIndexError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.index import XmlIndex
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.defaults import index_def_tab, DEFAULT_PREFIX, \
                                   INDEX_DEF_TABLE
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

IDX1 = "/testpackage/station/station/lon"
IDX2 = "/testpackage/station/station/lat"
IDX3 = "/testpackage/testml/testml/blah1/@id"
IDX4 = "/testpackage/station/station/XY/paramXY"

so_tests = ['so1.xml','so2.xml','so3.xml','so4.xml','so5.xml']
so_indexes = ['/sortordertests/sotest/sortorder/int1', 
              '/sortordertests/sotest/sortorder/int2', 
              '/sortordertests/sotest/sortorder/str1', 
              '/sortordertests/sotest/sortorder/str2']

class XmlIndexCatalogTest(SeisHubTestCase):
    #TODO: testGetIndexes
    _last_id=0
    _test_kp="station/XY/paramXY"
    _test_vp="/station"
    _test_uri="/stations/bern"
        
    def __init__(self, *args, **kwargs):
        super(XmlIndexCatalogTest,self).__init__(*args,**kwargs)
        self.catalog = self.env.catalog.index_catalog
        self.so_ids = list()
    
    def _setup_testdata(self):
        # create us a small test catalog
        self.res1=self.env.catalog.newXmlResource('testpackage','station',RAW_XML1)
        self.res2=self.env.catalog.newXmlResource('testpackage','station',RAW_XML2)
        self.res3=self.env.catalog.newXmlResource('testpackage','testml',RAW_XML3)
        idx1=self.env.catalog.newXmlIndex(IDX1)
        idx2=self.env.catalog.newXmlIndex(IDX2)
        idx3=self.env.catalog.newXmlIndex(IDX3)
        idx4=self.env.catalog.newXmlIndex(IDX4)
        self.env.catalog.addResource(self.res1)
        self.env.catalog.addResource(self.res2)
        self.env.catalog.addResource(self.res3)
        self.env.catalog.registerIndex(idx1)
        self.env.catalog.registerIndex(idx2)
        self.env.catalog.registerIndex(idx3)
        self.env.catalog.registerIndex(idx4)
        self.env.catalog.reindex(IDX1)
        self.env.catalog.reindex(IDX2)
        self.env.catalog.reindex(IDX3)
        self.env.catalog.reindex(IDX4)
        # add sort order test resources
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        test_path = os.path.join(path,'data')
        for f in so_tests:
            fh = open(test_path+os.sep+f, 'r')
            data = fh.read()
            fh.close()
            res = self.env.catalog.newXmlResource('sortordertests','sotest',
                                                  data)
            self.env.catalog.addResource(res)
            self.so_ids.append(res.uid)
        for i in so_indexes:
            idx = self.env.catalog.newXmlIndex(i)
            self.env.catalog.registerIndex(idx)
            self.env.catalog.reindex(i)
        
    def _cleanup_testdata(self):
        self.env.catalog.removeIndex(IDX1)
        self.env.catalog.removeIndex(IDX2)
        self.env.catalog.removeIndex(IDX3)
        self.env.catalog.removeIndex(IDX4)
        self.env.catalog.deleteResource(self.res1._id)
        self.env.catalog.deleteResource(self.res2._id)
        self.env.catalog.deleteResource(self.res3._id)
        for i in so_indexes:
            self.env.catalog.removeIndex(i)
        for id in self.so_ids:
            self.env.catalog.deleteResource(id)    
    
    def _assertClassAttributesEqual(self,first,second):
        return self.assertEquals(first.__dict__,second.__dict__)
    
    def _assertClassCommonAttributesEqual(self,first,second):
        # compare two classes' common attributes
        f = dict(first.__dict__)
        s = dict(second.__dict__)
        for k in s:
            if k not in f:
                f[k]=s[k]
        for k in f:
            if k not in s:
                s[k]=f[k]
        return self.assertEquals(f,s)
    
    def _assertClassAttributeListEqual(self,first,second,attribute_list):
        for attr in attribute_list:
            self.assertEqual(first.__getattribute__(attr),
                             second.__getattribute__(attr))
    
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
                 'key_path':test_kp,
                 'value_path':test_vp}
        query=("SELECT key_path,value_path FROM %(prefix)s%(table)s " + \
                "WHERE (key_path='%(key_path)s' AND value_path='%(value_path)s')") \
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
        self._assertClassAttributeListEqual(test_index, res, 
                                            ['key_path','value_path','type'])
        
        # remove:
        catalog.removeIndex(key_path=self._test_kp,
                            value_path=self._test_vp)
    
    def testIndexResource(self):
        dbmgr = XmlDbManager(self.db)
        catalog = XmlIndexCatalog(db = self.db,
                                  resource_storage = dbmgr)
        bad_catalog = XmlIndexCatalog(db = self.db)
        
        # register a test resource:
        test_res=XmlResource('testpackage','testtype', xml_data = RAW_XML1)
        try:
            dbmgr.addResource(test_res)
        except:
            print "Resource is already present in db."

        # register a test index:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp)
        catalog.registerIndex(test_index)
        
        # index test resource:
        catalog.indexResource(test_res._id, 
                              test_index.getValue_path(), 
                              test_index.getKey_path())
        
        # without storage:
        self.assertRaises(XmlIndexCatalogError,bad_catalog.indexResource,
                          test_res._id, 
                          test_index.getValue_path(), test_index.getKey_path())
        
        #TODO: check db entries made
                
        # pass invalid index args:
        self.assertRaises(InvalidIndexError, catalog.indexResource,
                          test_res._id, value_path="blub", key_path="blah")
        
        # clean up:
        catalog.removeIndex(key_path=self._test_kp, value_path=self._test_vp)
        dbmgr.deleteResource(test_res._id)
    
    def testFlushIndex(self):
        dbmgr=XmlDbManager(self.db)
        catalog=XmlIndexCatalog(self.db,dbmgr)
        #first register an index and add some data:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp)
        try:
            catalog.registerIndex(test_index)
        except:
            print "Error registering index."
        
        test_res = XmlResource('testpackage', 'testtype', xml_data = RAW_XML1)
        try:
            dbmgr.addResource(test_res)
        except:
            raise
            print "Error adding resource."
        #import pdb;pdb.set_trace()
        catalog.indexResource(test_res._id, test_index.getValue_path(),
                              test_index.getKey_path())
        #flush index:
        catalog.flushIndex(value_path=self._test_vp, 
                           key_path=self._test_kp)
        
        #TODO: check if index is properly flushed
        
        # clean up:
        catalog.removeIndex(test_index.getValue_path(), test_index.getKey_path())
        dbmgr.deleteResource(test_res._id)
        
#    def testQuery(self):
#        # create test catalog
#        self._setup_testdata()
#        
#        q0 = "/station[lon != 12.51200 and lat = 55.23200]"
#        q1 = "/station[lat]"
#        q2 = "/station[XY/paramXY or lon = 12.51200]"
#        q3 = "/testml"
#
#        res0 = self.catalog.query(XPathQuery(q0))
#        res1 = self.catalog.query(XPathQuery(q1))
#        res2 = self.catalog.query(XPathQuery(q2))
#        res3 = self.catalog.query(XPathQuery(q3))
#        res0.sort(); res1.sort(); res2.sort(); res3.sort()
#        self.assertEqual(res0, [self.res2.uid])
#        self.assertEqual(res1, [self.res1.uid, self.res2.uid])
#        self.assertEqual(res2, [self.res1.uid, self.res2.uid])
#        self.assertEqual(res3, [self.res3.uid])
#
#        # sort order tests
#        so1 = "/sotest[int1]"
#        so2 = "/sotest"
#        res1 = self.catalog.query(XPathQuery(so1, [["/sotest/int1","asc"]]))
#        print res1
##        res2 = self.catalog.query(XPathQuery(so1, [["/sortorder/int1","desc"]], 
##                                             limit = 3))
##        res3 = self.catalog.query(XPathQuery(so1, [["/sortorder/int2","asc"],
##                                                   ["/sortorder/str2","desc"]], 
##                                             limit = 5))
##        res4 = self.catalog.query(XPathQuery(so2,[["/sortorder/int2","desc"]],
##                                             limit = 3))
##        
##        sot_res = ['/so/'+st for st in so_tests]
##        self.assertEqual(res1,sot_res)
##        sot_res.reverse()
##        self.assertEqual(res2,sot_res[:3])
##        sot_res.reverse()
##        self.assertEqual(res3,[sot_res[0],sot_res[3],sot_res[4],
##                               sot_res[1],sot_res[2]])
##        self.assertEqual(res4,[sot_res[1],sot_res[2],sot_res[0]])
#        
#        # remove test catalog
#        self._cleanup_testdata()

        
class QueryAliasesTest(SeisHubTestCase):
    def testQueryAliases(self):
        aliases = QueryAliases(self.env.db)
        aliases["blah"] = "/blah[/blah/blah]"
        aliases["blah2"] = "/blah[popoppoo]"
        aliases["blah3"] = "/blah[dududuuu]"
        self.assertEquals(aliases["blah"],"/blah[/blah/blah]")
        aliases["blah"] = "/andererpfad"
        self.assertEquals(aliases.get("blah"),"/andererpfad")   
        self.assertEquals(aliases["blah"],"/andererpfad")
        self.assertEquals("blah" in aliases, True)
        del aliases["blah"]
        self.assertEquals("blah" in aliases, False)
        del aliases["blah2"]
        del aliases["blah3"]


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexCatalogTest, 'test'))
    suite.addTest(unittest.makeSuite(QueryAliasesTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')