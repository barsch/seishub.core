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
        
    def deleteResource(uri):
        """Delete an existing resource"""
        
    def getResource(uri):
        """Retreive an existing resource from the storage"""
             
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
        
    def getValues():
        """@return: values of this index"""
    
    def eval(xml_resource):
        """Evaluate this index on a given XmlResource
        @param xml_resource: xmldb.xmlresource.XmlResource object
        @return: list with key, value pairs on success, None else"""
        
class IIndexRegistry(Interface):
    """Manages index creation, retrieval, update and removal"""
    
    def registerIndex(xml_index):
        """@param xml_index: register given XmlIndex
        @return: deferred which will fire the unique index id on success
        """
    
    def removeIndex(xml_index=None,
                    key_path=None,value_path=None):
        """Remove an index and its data.
        All indexed data belonging to the index will be removed.
        To update an existing index without data loss use updateIndex.
        Pass an id or a key_path and value_path or a XmlIndex instance
        @param id: id
        @param key_path: key path
        @param value_path: value path
        @param xml_index: XmlIndex instance 
        @return: Deferred"""
        
    def updateIndex(old_index=None,new_index=None):
        """@param id: internal index id
        @param xml_index: new XmlIndex instance
        @param id: id of index to be updated"""
        
    def getIndex(key_path,value_path):
        """@return: Deferred which will return a XmlIndex on success"""
        
class IResourceIndexing(Interface):
    """Index resources"""
    def indexResource(resource,
                      xml_index=None,
                      key_path=None,value_path=None):
        """Index a resource at the first time.
        Pass either a XmlIndex instance or a key_path, value_path pair
        
        @param resource: IXmlResource to be indexed
        @param xml_index: IXmlIndex
        @param key_path: key path
        @param value_path: value path
        @return: Deferred returning True on success
        """
        
    def reindexResources(resource_storage,
                         xml_index=None,
                         key_path=None,value_path=None):
        """Reindex the given index. 
        Which means all resources the index applies to (determined by 
        value_path) are read from the given storage and reevaluated.
        Formerly indexed data is beeing deleted thereby.
        
        @param xml_index: IXmlIndex
        @param key_path: key path
        @param value_path: value path
        @param resource_storage: IResourceStorage providing access to resources
        """
        
    def flushIndex(xml_index=None,
                   key_path=None,value_path=None):
        """Remove all indexed data for given index.
        To completely remove an index use removeIndex.
        
        @param xml_index: IXmlIndex
        @param key_path: key path
        @param value_path: value path
        @return: Deferred"""
        
class IXmlIndexCatalog(Interface):
    """Catalog providing methods for xml resource indexing and searching
    """
    
    def init(adbapi_connection):
        """@param adbapi_connection: an adbapi conform db connector"""

    def query(query):
        """Drop a query on the catalog"""

        