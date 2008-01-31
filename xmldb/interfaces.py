# -*- coding: utf-8 -*-

from zope.interface import Interface

class IXmlCatalog(Interface):
    """This is the main interface to access the whole xmldb thing"""
    
    def newXmlResource(uri,xml_data):
        """Resource factory; supposed to be used with addResource from 
        IResourceStorage
        @param raw_data: string containing xml data
        @param uri: uri of the new resource
        @return: XmlResource instance"""
        
    def newXmlIndex(xpath_expr,type):
        """Index factory; supposed to be used with registerIndex
        @param xpath_expr: index defining xpath expression
        @param type: index type (e.g. "text", "int")
        @return: XmlIndex instance"""
        
    def listIndexes(res_type = None, data_type = None):
        """@param res_type: restrict results to specified resource type
        @type res_type: string 
        @param data_type: restrict results to a specified data type (string)
        @type data_type: string 
        @return: list of XmlIndexes
        @rtype: list"""
    
    def query(xpath_query):
        """@param xpath_query: restricted xpath expression (see xpath.py for 
        further information)"""

class IXmlResource(Interface):
    """XmlResource is a subclass of Resource providing some special xml 
    functionality such as xml validation and parsing
    """
    def getXml_doc():
        """@return: xml document object"""
        
    def setXml_doc(xml_doc):
        """@param xml_doc: xml document object as provided by a xml parser,
        must implement seishub.interfaces.ixml.IXmlDoc"""
        
    def getResourceType(self):
        """the resource type is determined by the root node of the underlying 
        xml document
        @return: resource type (string)"""
        
    def setData(xml_data):
        """@param data: raw xml data as a string"""
        
    def getData(self):
        """@return: xml data (string)"""
        
    def getUri(self):
        """@return: uri (string)"""
        
class IResourceStorage(Interface):
    """Basic XML storage manager description"""
    
    def addResource(xmlResource):
        """Add a new resource to the storage"""
        
    def updateResource(xmlResource):
        """Update an existing resource"""
        
    def deleteResource(uri):
        """Delete an existing resource"""
        
    def getResource(uri):
        """Retreive an existing resource from the storage"""
        
    def getUriList(self,type):
        """Return a list of all registered uris
        or the subset of uris corresponding to resources of type 'type'
        @return: a list of uris"""
             
class IXmlIndex(Interface):
    """Xml index base class
    
    __init__ expects a pair of key_path / value_path,
    and optionally a index type (default: "text")"""
        
    def setValueKeyPath(value_path,key_path):
        """@param value_path: new value path
        @param key_path: new key_path"""
    
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
    
    def removeIndex(xpath_expr=None,key_path=None,value_path=None):
        """Remove an index and its data.
        All indexed data belonging to the index will be removed.
        To update an existing index without data loss use updateIndex.
        Pass an id or a key_path and value_path or a XmlIndex instance
        @param key_path: key path
        @param value_path: value path
        @param xpath_expr: index defining xpath expression 
        @return: Deferred"""
        
    def updateIndex(xpath_expr,new_index):
        """@param xml_index: new XmlIndex instance
        @param xpath_expr: index defining xpath expression"""
        
    def getIndex(xpath_expr=None,key_path=None,value_path=None):
        """@return: Deferred which will return a XmlIndex on success"""
        
    def getIndexes(res_type=None,key_path=None,data_type=None):
        """@param res_type: resource type (string)
        @param key_path: key path (string)
        @param data_type: data type (string, e.g. "text", "int")
        @return: list of indexes consistent with the given constraints"""
        
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

        