# -*- coding: utf-8 -*-

from zope.interface.exceptions import DoesNotImplement

from twisted.trial.unittest import TestCase
from twisted.enterprise import adbapi
from twisted.enterprise import util as dbutil

from seishub.xmldb.xmlcatalog import XmlCatalog
from seishub.xmldb.xmlcatalog import XmlCatalogError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.xmlresource import XmlResource

from seishub.defaults import DB_DRIVER,DB_ARGS, INDEX_DEF_TABLE, DEFAULT_PREFIX

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

class XmlCatalogTest(TestCase):
    def setUp(self):
        self._dbConnection=adbapi.ConnectionPool(DB_DRIVER,**DB_ARGS)
        self._last_id=0
        self._test_kp="XY/paramXY"
        self._test_vp="/station"
        
        
    def tearDown(self):
        # make sure created indexes are removed in the end, 
        # even if not all tests pass:
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)
        #d=self.__cleanUp()
        #return d
    
    def _assertClassAttributesEqual(self,first,second):
        return self.assertEquals(first.__dict__,second.__dict__)
    
    def __cleanUp(self,res=None):
        # manually remove db entries created
        query=("DELETE FROM %(prefix)s_%(table)s WHERE " + \
               "(value_path=%(value_path)s AND key_path=%(key_path)s)") % \
               {'prefix':DEFAULT_PREFIX,
                'table':INDEX_DEF_TABLE,
                'key_path':dbutil.quote(self._test_kp,"text"),
                'value_path':dbutil.quote(self._test_vp,"text")}
        d=self._dbConnection.runOperation(query)
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

            d=self._dbConnection.runQuery(query) \
             .addCallback(lambda res: self.assertEquals(res[0],[test_kp,test_vp]))
            return d
        
        # register an index:
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)        
        test_index=XmlIndex(key_path=test_kp,
                            value_path=test_vp
                            )
        
        d=catalog.registerIndex(test_index)
        d.addCallback(_checkResults)
        
        # try to add a duplicate index:
        d.addCallback(lambda m: catalog.registerIndex(test_index))
        self.assertFailure(d,XmlCatalogError)
        
        # clean up:
        d.addCallback(self.__cleanUp)

        return d
    
    def testRemoveIndex(self):
        # first register an index to be removed:
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)
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
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)
        test_index=XmlIndex(key_path=self._test_kp,
                            value_path=self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        def get_id(id):
            self._last_id=int(id)
        d.addCallback(get_id)
        
        # get by key:
        d.addCallback(catalog.getIndex,
                      key_path = self._test_kp,value_path = self._test_vp)
        
        #d.addCallback(self._assertClassEquals,test_index)
        d.addCallback(self._assertClassAttributesEqual,test_index)
        # get by id:
        d.addCallback(lambda m: catalog.getIndex(id=self._last_id))
        d.addCallback(self._assertClassAttributesEqual,test_index)
        
        # remove :
        d.addCallback(lambda m: catalog.removeIndex(key_path=self._test_kp,
                                                    value_path=self._test_vp))
       
        return d
    
    def testIndexResource(self):
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)
        
        class Foo:
            pass
        self.assertRaises(DoesNotImplement,catalog.indexResource, Foo(), 1)

        test_res=XmlResource(uri = '/stations/bern', xml_data = RAW_XML1)

        # register a test index:
        test_index=XmlIndex(key_path = self._test_kp,
                            value_path = self._test_vp
                            )
        d=catalog.registerIndex(test_index)
        
        # index resource:
        #d.addCallback(lambda foo: catalog.indexResource(test_res,test_index))
        #def printErr(err):
        #    print err
        #d.addErrback(printErr)
        
        # clean up:
        d.addCallback(self.__cleanUp)
        
