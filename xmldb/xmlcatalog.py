# -*- coding: utf-8 -*-
#from seishub.core import implements
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeishubError

from seishub.xmldb.interfaces import IXmlCatalog

from seishub.dbspecific import DEFAULT_PREFIX, INDEX_DEF_TABLE

from seishub.dbspecific import ADD_INDEX_QUERY, DELETE_INDEX_QUERY, \
                               GET_NEXT_ID_QUERY
#                       REGISTER_URI_QUERY, REMOVE_URI_QUERY, \
#                       QUERY_STR_MAP, GET_RESOURCE_BY_URI_QUERY


class XmlCatalog(object):
    implements(IXmlCatalog)
    
    def __init__(self,adbapi_connection):
        if not hasattr(adbapi_connection,'runInteraction'):
            raise TypeError("adbapi connector expected!")
            self._db=None
        else:
            self._db=adbapi_connection
        
    def registerIndex(self,xml_index):
        def _addIndexTxn(txn):
            # get next unique id:
            get_next_id_query=GET_NEXT_ID_QUERY % (DEFAULT_PREFIX,
                                                   INDEX_DEF_TABLE)
            txn.execute(get_next_id_query)
            next_id=txn.fetchall()[0][0]
            # insert into INDEX_DEF_TABLE:
            add_res_query=ADD_INDEX_QUERY % (DEFAULT_PREFIX,INDEX_TABLE,
                                             next_id,
                                             dbutil.quote(xml_resource.getData(),
                                                          "text"))
            txn.execute(add_res_query)
            return next_id
        
        d=self.db.runInteraction(_addIndexTxn)
        return d
    
    
        
        