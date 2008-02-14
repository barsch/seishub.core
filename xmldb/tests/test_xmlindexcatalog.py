# -*- coding: utf-8 -*-

from twisted.enterprise import util as dbutil

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalogError, \
                                          InvalidIndexError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.xmlresource import XmlResource

from seishub.xmldb.defaults import INDEX_DEF_TABLE, DEFAULT_PREFIX

RAW_XML1="""<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <paramXY>20.5</paramXY>
        <paramXY>11.5</paramXY>
        <paramXY>blah</paramXY>
    </XY>
</station>"""

class XmlIndexCatalogTest(SeisHubTestCase):
    #TODO: testGetIndexes
    def setUp(self):
        super(XmlIndexCatalogTest,self).setUp()
        self._last_id=0
        self._test_kp="XY/paramXY"
        self._test_vp="/station"
        self._test_uri="/stations/bern"
        
        
    def tearDown(self):
        # make sure created indexes are removed in the end, 
        # even if not all tests pass:
        
        # catalog=XmlIndexCatalog(adbapi_connection=self.db)
        d=self.__cleanUp()
        return d
    
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
        query=("DELETE FROM %(prefix)s%(table)s WHERE " + \
               "(value_path=%(value_path)s AND key_path=%(key_path)s)") % \
               {'prefix':DEFAULT_PREFIX,
                'table':INDEX_DEF_TABLE,
                'key_path':dbutil.quote(self._test_kp,"text"),
                'value_path':dbutil.quote(self._test_vp,"text")}
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
        self.__cleanUp
    
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
        
        test_res=XmlResource(uri = self._test_uri, xml_data = RAW_XML1)
        try:
            dbmgr.addResource(test_res)
        except:
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
    
    def test_parse_xpath_query(self):
        #TODO: test_parse_xpath_query
        test_query="/station[./lat=50.23200]"
        #print XmlIndexCatalog._parse_xpath_query(test_query)
        
        
