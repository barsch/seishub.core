# -*- coding: utf-8 -*-

from zope.interface.exceptions import DoesNotImplement

from twisted.enterprise import util as dbutil

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalogError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.xmlresource import XmlResource

from seishub.defaults import INDEX_DEF_TABLE, DEFAULT_PREFIX

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
    def setUp(self):
        super(XmlIndexCatalogTest,self).setUp()
        self._last_id=0
        self._test_kp="XY/paramXY"
        self._test_vp="/station"
        self._test_uri="/stations/bern"
        
        
    def tearDown(self):
        # make sure created indexes are removed in the end, 
        # even if not all tests pass:
        
        catalog=XmlIndexCatalog(adbapi_connection=self.db)
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
               
        query=("DELETE FROM %(prefix)s_%(table)s WHERE " + \
               "(value_path=%(value_path)s AND key_path=%(key_path)s)") % \
               {'prefix':DEFAULT_PREFIX,
                'table':INDEX_DEF_TABLE,
                'key_path':dbutil.quote(self._test_kp,"text"),
                'value_path':dbutil.quote(self._test_vp,"text")}
        d=self.db.runOperation(query)
        return d
    
    def testRegisterIndex(self):
        test_kp=self._test_kp
        test_vp=self._test_vp
        
        def _checkResults(obj):
            str_map={'prefix':DEFAULT_PREFIX,
                     'table':INDEX_DEF_TABLE,
                     'key_path':dbutil.quote(test_kp,"text"),
                     'value_path':dbutil.quote(test_vp,"text")}
            query=("SELECT key_path,value_path FROM %(prefix)s_%(table)s " + \
                "WHERE (key_path=%(key_path)s AND value_path=%(value_path)s)") \
                % (str_map)

            d=self.db.runQuery(query) \
             .addCallback(lambda res: self.assertEquals(res[0],[test_kp,test_vp]))
            return d
        
        # register an index:
        catalog=XmlIndexCatalog(adbapi_connection=self.db)        
        test_index=XmlIndex(key_path=test_kp,
                            value_path=test_vp
                            )
        
        d=catalog.registerIndex(test_index)
        d.addCallback(_checkResults)
        
        # try to add a duplicate index:
        d.addCallback(lambda m: catalog.registerIndex(test_index))
        self.assertFailure(d,XmlIndexCatalogError)
        
        # clean up:
        d.addCallback(self.__cleanUp)

        return d
    
    def testRemoveIndex(self):
        # first register an index to be removed:
        catalog=XmlIndexCatalog(adbapi_connection=self.db)
        test_index=XmlIndex(key_path=self._test_kp,
                            value_path=self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        
        # remove after registration has finished:
        d.addCallback(lambda m: catalog.removeIndex(key_path=self._test_kp,
                                                    value_path=self._test_vp))
        return d
    
    def testGetIndex(self):
        # first register an index to grab, and retrieve it's id:
        catalog=XmlIndexCatalog(adbapi_connection=self.db)
        test_index=XmlIndex(key_path=self._test_kp,
                            value_path=self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        
        #TODO: invalid index should raise exception
                
        # get by key:
        d.addCallback(lambda foo: 
                      catalog.getIndex(key_path = self._test_kp,
                                       value_path = self._test_vp))
        d.addCallback(self._assertClassCommonAttributesEqual,test_index)
        
        # remove:
        d.addCallback(lambda m: catalog.removeIndex(key_path=self._test_kp,
                                                    value_path=self._test_vp))
       
        return d
    
    def testIndexResource(self):
        catalog=XmlIndexCatalog(adbapi_connection=self.db)
        
        class Foo:
            pass
        self.assertRaises(DoesNotImplement,catalog.indexResource, Foo(), 1)
        
        # register a test resource:
        dbmgr=XmlDbManager(self.db)
        test_res=XmlResource(uri = self._test_uri, xml_data = RAW_XML1)
        dbmgr.addResource(test_res)

        # register a test index:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        def printRes(res):
            print res
            return res
        
        # index a test resource:
        d.addCallback(lambda f: 
                      catalog.indexResource(test_res, xml_index=test_index))
        
        #TODO: check db entries made
                
        # pass invalid index args:
        d.addCallback(lambda f: catalog.indexResource(test_res, 
                                                      key_path="blah",
                                                      value_path="blub"))
        self.assertFailure(d,XmlIndexCatalogError)
        d.addErrback(self._printRes)
        # clean up:
        d.addBoth(lambda f: catalog.removeIndex(key_path=self._test_kp, 
                                                value_path=self._test_vp)) \
         .addBoth(lambda f: dbmgr.deleteResource(self._test_uri))
        return d
    
    def testFlushIndex(self):
        catalog=XmlIndexCatalog(adbapi_connection=self.db)
        #first register an index and add some data:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        dbmgr=XmlDbManager(self.db)
        test_res=XmlResource(uri = self._test_uri, xml_data = RAW_XML1)
        dbmgr.addResource(test_res)
        
        d.addCallback(lambda idx_id: catalog.indexResource(test_res,
                                                           test_index))
        #flush index:
        d.addCallback(lambda foo: catalog.flushIndex(key_path=self._test_kp,
                                                     value_path=self._test_vp))
        #TODO: check if index is properly flushed
        d.addErrback(self._printRes)
        # clean up:
        d.addBoth(lambda f: catalog.removeIndex(test_index)) \
         .addBoth(lambda f: dbmgr.deleteResource(self._test_uri))
        
        return d
    
    def test_parse_xpath_query(self):
        #TODO: test_parse_xpath_query
        test_query="/station[./lat=50.23200]"
        print XmlIndexCatalog._parse_xpath_query(test_query)
        
        
