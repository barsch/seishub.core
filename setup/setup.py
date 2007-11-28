# -*- coding: utf-8 -*-

from twisted.enterprise import adbapi
from twisted.internet import reactor
from twisted.internet.defer import DeferredList

from seishub.defaults import DB_DRIVER,DB_ARGS,CREATES

def _log_errors(results):
    for res in results: 
        if res[0]==False:
            print res[1]
    return results
            
def _db_transaction(txn,query_list):
    """Perform the queries in query_list in the given order as a transaction.
    returns a list of query results
    """
    result_list=list()
    for query in query_list:
        txn.execute(query)
        try:
            res=txn.fetchall()
        except:
            res=None
        result_list.append(res)
    return result_list
    
if __name__ == "__main__":     
    conn=adbapi.ConnectionPool(DB_DRIVER,**DB_ARGS)
    stop_reactor=lambda _: reactor.stop()
    query_list=CREATES
    
    d=list()
    
    d.append(conn.runInteraction(_db_transaction,query_list))
    
    dl=DeferredList(d,consumeErrors=True)
    dl.addCallback(_log_errors).addCallback(stop_reactor)
    
    reactor.run()