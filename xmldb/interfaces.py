# -*- coding: utf-8 -*-

from zope.interface import Interface

class IXmlResource(Interface):
    """XmlResource is a subclass of Resource providing some special xml 
    functionality such as xml validation and parsing
    """
    def getXml_doc():
        """@return: xml document object"""
        
    def setXml_doc(xml_doc):
        """@param xml_doc: xml document object as provided by a xml parser,
        must implement seishub.interfaces.ixml.IXmlDoc"""
        
    def setData(xml_data):
        """@param data: raw xml data as a string"""
        
class IResourceStorage(Interface):
    """Basic XML Storage Manager Description"""
    
    def addResource(xmlResource):
        """Add a new resource to the storage"""
        
    def updateResource(xmlResource):
        """Update an existing resource"""
        
    def deleteResource(URI):
        """Delete an existing resource"""
        
    def getResource(URI):
        """Retreive an existing resource from the storage"""
        
    #def query(query_str):
    #    """Query the storage"""
        
class IXmlIndex(Interface):
    """Xml index base class
    
    __init__ expects a pair of key_path / value_path
    or a full xpath expression instead"""
    
    def setKey_path(path):
        """@param path: new key path"""
        
    def setValue_path(path):
        """@param path: new value path"""
    
    def getKey_path():
        """@return: my key path"""
        
    def getValue_path():
        """@return: my value path"""
        
    def getType():
        """@return: data type of the index key"""
    
    def eval(xml_resource):
        """Evaluate this index on a given XmlResource
        @param xml_resource: xmldb.xmlresource.XmlResource object
        @return: list with key, value pairs on success, None else"""
        
class IXmlCatalog(Interface):
    """Catalog providing methods for xml resource indexing and searching
    
    Register an index:
    >>> from twisted.enterprise import adbapi
    >>> from seishub.xmldb.xmlcatalog import XmlCatalog
    >>> from seishub.xmldb.xmlindex import XmlIndex
    >>> from seishub.defaults import DB_DRIVER,DB_ARGS
    >>> dbConnection=adbapi.ConnectionPool(DB_DRIVER,**DB_ARGS)
    >>> index=XmlIndex(key_path="blah/blah",value_path="/station")
    >>> catalog=XmlCatalog(adbapi_connection=dbConnection)
    >>> d=catalog.registerIndex(index)
    
    Remove index created above:
    ...
    
    Run reactor:
    >>> from twisted.internet import reactor 
    >>> d=d.addCallback(lambda o: reactor.stop())
    >>> reactor.run()
    """
    
    def init(adbapi_connection):
        """@param adbapi_connection: an adbapi conform db connector"""
    
    def registerIndex(xml_index):
        """@param xml_index: register given XmlIndex
        @return: unique index id
        
        
        """
        
    def removeIndex(id,key_path,value_path):
        """Remove index with given id or key path, value path pair
        @param id: id
        @param key_path key path:
        @param value_path: value path"""
        
    def updateIndex(xml_index,id):
        """@param xml_index: new XmlIndex instance
        @param id: id of index to be updated"""
        
    def getIndex(id,key_path,value_path):
        """@return: XmlIndex with given id or key_path,value_path"""
        
    def indexResource(resource,index_id):
        """Index a resource at the first time.
        
        @param resource: IXmlResource to be indexed
        @param index_id: id of index to be applied
        """
        
    def reindexResources(index_id,resource_storage):
        """Reindex the given index. 
        Which means all resources the index applies to (determined by 
        value_path) are read from the given storage and reevaluated.
        Formerly indexed data is beeing deleted thereby.
        
        @param index_id: id of index beeing reindexed
        @param resource_storage: IResourceStorage providing access to resources
        """
        
    def query(query,index=None):
        """Drop a query on the catalog"""
        
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
        