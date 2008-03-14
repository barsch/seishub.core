# -*- coding: utf-8 -*-

from zope.interface import Interface

class IXmlCatalog(Interface):
    """This is the main interface to access the whole xmldb thing"""
    
    def newXmlResource(uri,xml_data):
        """Resource factory; supposed to be used with addResource from 
        IResourceStorage
        @param xml_data: string containing xml data
        @param uri: uri of the new resource
        @return: XmlResource instance"""
        
    def newXmlIndex(xpath_expr,type):
        """Index factory; supposed to be used with registerIndex
        @param xpath_expr: index defining xpath expression
        @param type: index type (e.g. "text", "int")
        @return: XmlIndex instance"""
        
    def listIndexes(res_type = None, data_type = None):
        """Return a list of registered indexes. 
        (Optionally) indexes with the given parameters only: 
        @param res_type: restrict results to specified resource type
        @type res_type: string 
        @param data_type: restrict results to a specified data type (string)
        @type data_type: string 
        @return: list of XmlIndexes
        @rtype: list"""
    
    def query(xpath_query):
        """Query the catalog and return a list of URIs
        where xpath_query is a XPath Query like string. 
        (see L{seishub.xmldb.xpath.XPathQuery} and
        L{seishub.xmldb.xpath.RestrictedXpathExpression})
        
        The following query types are supported by now (but may still be 
        unstable though):
        
         - B{resource type queries}:
         
           "/resource_type"
           
           return all registered URIs with given resource type
           
         - B{index queries}:
         
           "/resource_type[key_path1 operator value (and|or) 
           key_path2 operator value ...] 
           
           where operator can be: =, !=, <, >, <=, >=
        
        @param xpath_query: restricted xpath expression
        @type xpath_query: string
        @return: list of URIs
        @rtype: python list"""

class IXmlResource(Interface):
    """XmlResource is a subclass of Resource providing some special xml 
    functionality such as xml validation and parsing
    """
    def getXml_doc():
        """@return: xml document object"""
        
    def setXml_doc(xml_doc):
        """@param xml_doc: xml document object as provided by a xml parser,
        must implement seishub.util.libxmlwrapper.ixml.IXmlDoc"""
        
    def getResourceType(self):
        """the resource type is determined by the root node of the underlying 
        xml document
        @return: resource type (string)"""
        
    def setData(xml_data):
        """@param xml_data: raw xml data
        @type xml_data: string"""
        
    def getData(self):
        """@return: xml data (string)"""
        
    def getUri(self):
        """@return: uri (string)"""
        
class IResourceTypeRegistry(Interface):
    """Handles resource type specific meta data, such as XML Schema definitions 
    """
    
    def registerResourceType(type, xml_schema):
        """Define new resource type using given XML schema
        @param type: Name of the new type
        @type type: string
        @param xml_schema: XML Schema definition
        @type xml_schema: L{seishub.xmldb.interfaces.IXmlResource}"""
        
    def removeResourceType(type):
        """Remove all information about given resource type, but leave 
        resources of that type untouched.
        @param type: Name of type to be removed
        @type type: string"""
        
    def getSchema(type):
        """Get XML Schema definition for given resource type.
        @param type: Name of a resource type
        @type type: string
        @return: XML Schema definition
        @rtype: L{seishub.xmldb.interfaces.IXmlResource}"""
        
    def listResourceTypes():
        """@return: list of known resource types
        @rtype: python list"""
        
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
        """@param new_index: new XmlIndex instance
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
    def indexResource(uri, value_path, key_path):
        """Index the given resource with the given index.
        
        @param uri: uri of resource to be indexed
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
        
    def flushIndex(value_path, key_path):
        """Remove all indexed data for given index.
        To completely remove an index use removeIndex.

        @param value_path: value path
        @param key_path: key path
        @return: True on success"""
        
class IXmlIndexCatalog(Interface):
    """Catalog providing methods for xml resource indexing and searching
    """
    
    def init(adbapi_connection):
        """@param adbapi_connection: an adbapi conform db connector"""

    def query(query):
        """Drop a query on the catalog
        @param query: xpath query to be performed
        @type query: L{seishub.xmldb.interfaces.IXPathQuery}
        @return: result set containing uris of resources this query applies to
        @rtype: list of strings"""

class IXPathQuery(Interface):
    def getPredicates():
        """Get parsed predicates
        @return: parsed predicate expression
        @rtype: L{seishub.xmldb.xpath.PredicateExpression}"""
        
    def getValue_path():
        """Get value path
        @return: value path this query corresponds to
        @rtype: string"""
        
    def has_predicates():
        """@return: True if query has predicates
        @rtype: True | False"""