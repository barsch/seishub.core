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
    """Xml index base class, without specified data type
    
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
        
    def getValue():
        """@return: result after applying index to a given resource"""
    
    def eval(xml_resource):
        """Evaluate this index on a given XmlResource
        @param xml_resource: xmldb.xmlresource.XmlResource object
        @return: self on success, None else"""
        
class IXmlCatalog(Interface):
    """Catalog providing methods for indexing, managing and searching resources
    """
    def init(adbapi_connection):
        """@param adbapi_connection: an adbapi conform db connector"""
    
    def registerIndex(xml_index):
        """@param xml_index: register given XmlIndex
        @return: unique index id"""
        
    def removeIndex(id):
        """@param id: id of xml index to be removed"""
        
    def updateIndex(xml_index,id):
        """@param xml_index: new XmlIndex instance
        @param id: id of index to be updated"""
        
    def getIndex(id):
        """@return: XmlIndex with given id"""
        
    def query(query,index=None):
        """Drop a query on the catalog"""
        