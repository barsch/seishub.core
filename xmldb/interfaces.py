# -*- coding: utf-8 -*-

from zope.interface import Interface

class IXmlCatalog(Interface):
    """This is the main interface to access all xmldb related classes"""
    
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
    
    def query(query, order_by = None, limit = None):
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
           
        B{Order by clauses}
        
        (see also: L{seishub.xmldb.xpath.XPathQuery})
        
        One can order search results via order by clauses and also specify a 
        limit to the number of returned results.
        Order by clauses are of the following form::
         order_by = [["/resource_type/sortindex1","asc|desc"],
                     ["/resource_type/sortindex2","asc|desc"],
                    ... ]
        
        @param query: restricted xpath expression
        @type query: string
        @param order_by: List of order by clauses
        @type order_by: python list
        @param limit: limit number of results
        @type limit: int   
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
        must implement seishub.util.xml.IXmlDoc"""
        
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
        
class IIndex(Interface):
    def init(value_path=None, key_path=None, type="text"):
        pass
    
    def setValueKeyPath(value_path,key_path):
        """@param value_path: new value path
        @param key_path: new key_path"""
    
    def getKey_path():
        """@return: key path"""
        
    def getValue_path():
        """@return: value path"""
        
    def getType():
        """@return: data type of the index key"""
        
    def getValues():
        """@return: values of this index"""
             
class IXmlIndex(IIndex):
    """An XmlIndex is used in order to index data stored inside a XmlResource's
    XML structure
    """
    
    def eval(xml_resource):
        """Evaluate this index on a given XmlResource
        @param xml_resource: xmldb.xmlresource.XmlResource object
        @return: list with key, value pairs on success, None else"""

class IVirtualIndex(IIndex):
    """A VirtualIndex is used in order to make additional information about a XmlResource 
    available to the index"""
        
    def setValue(data):
        """set value of virtual index
        @param data: any data of correct type"""
        
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
    def init(query, order_by = None, limit = None):
        """@param param: XPath query
        @type query: string
        @param order_by: list of order by clauses of the form: 
        [["/somenode/someelement/@someattribute" (, "ASC"|"DESC")], 
        ...]
        @type order_by: python list
        @param limit: maximum number of results
        @type limit: int"""
        
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

    def getOrder_by():
        """@return: List of parsed order by clauses
        @rtype: python list"""
    
    def getLimit():
        """@return: Result set limit (maximum number of results)
        @rtype: integer"""
        
class IXPathExpression(Interface):
    """Parsed XPath expression for use with the index catalog"""
    def __init__(expr):
        """@param expr: XPath expression
        @type expr: string"""
        
class IDbEnabled(Interface):
    """Object provides access to db manager"""
    def setDb(db):
        """@param db: database engine"""
        
    def getDb():
        """@return: database engine"""
        
class ISerializable(Interface):
    """Object providing functionality for serialization"""
    def _getId():
        """return internal storage id"""
    
    def _setId(self, id):
        """set internal storage id"""
    
    def getFields():
        """@return: dict of the form {'fieldname':value}"""