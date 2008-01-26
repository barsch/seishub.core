# -*- coding: utf-8 -*-
from zope.interface import implements
from twisted.enterprise import adbapi

from seishub.defaults import DB_DRIVER
from seishub.xmldb.interfaces import IXmlCatalog, IResourceStorage
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog

class XmlCatalog(object):
    implements(IXmlCatalog,
               IResourceStorage)
    
    def __init__(self,env):
        print "HUHUHUHUHUHUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"
        self.env=env
        db_str=self.env.config.get('seishub','database')
        self._db=adbapi.ConnectionPool(DB_DRIVER,db_str)
    
    # methods from IXmlCatalog:
    
    def newXmlResource(raw_data,uri):
        pass
    
    