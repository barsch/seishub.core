# -*- coding: utf-8 -*-

from zope.interface.exceptions import DoesNotImplement

from twisted.trial.unittest import TestCase
from twisted.enterprise import adbapi
from twisted.enterprise import util as dbutil

from seishub.xmldb.xmlcatalog import XmlCatalog
from seishub.xmldb.xmlcatalog import XmlCatalogError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindex import XmlIndex

from seishub.defaults import DB_DRIVER,DB_ARGS, INDEX_DEF_TABLE, DEFAULT_PREFIX

class XmlCatalogTest(TestCase):
    def setUp(self):
        self._dbConnection=adbapi.ConnectionPool(DB_DRIVER,**DB_ARGS)
    
    def testRegisterIndex(self):
        test_kp="lon"
        test_vp="/station"
        
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
        
        def _cleanUp(res):
            # manually remove db entries created
            query=("DELETE FROM %(prefix)s_%(table)s WHERE " + \
                "(value_path=%(value_path)s AND key_path=%(key_path)s)") % \
                {'prefix':DEFAULT_PREFIX,
                 'table':INDEX_DEF_TABLE,
                 'key_path':dbutil.quote(test_kp,"text"),
                 'value_path':dbutil.quote(test_vp,"text")}
            d=self._dbConnection.runOperation(query)
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
        d.addCallback(_cleanUp)

        return d
    
    def testRemoveIndex(self):
        # first register an index to be removed
        catalog=XmlCatalog(adbapi_connection=self._dbConnection)
        test_index=XmlIndex(key_path="lat",
                            value_path="/station"
                            )
        d=catalog.registerIndex(test_index)
        
        # remove after registration has finished:
        d.addCallback(lambda m: catalog.removeIndex(key_path="lat",
                                                    value_path="/station"))
       
        return d
    
    
