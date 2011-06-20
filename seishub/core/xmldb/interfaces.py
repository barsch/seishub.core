# -*- coding: utf-8 -*-

from seishub.core.core import Interface, Attribute


class IResource(Interface):
    """
    Marker interface for the xmldb resources.
    """
    id = Attribute("Id of resource (Integer)")
    revision = Attribute("Revision of that resource")
    resource_id = Attribute("Unique id of related XML resource")
    package_id = Attribute("Package id, that resource belongs to")
    resourcetype_id = Attribute("Resourcetype id, that resource is type of")
    version_control = Attribute("Boolean, specifies if version control is" + \
                                "enabled or disabled for related resource")


class IDocumentMeta(Interface):
    """
    Marker interface for xmldb document-specific metadata objects.
    """
    pass


class IXmlDocument(Interface):
    """
    Marker interface for xmldb XML documents.
    """
    def getXml_doc(): #@NoSelf
        """
        @return: xml document object
        """

    def setXml_doc(xml_doc): #@NoSelf
        """
        @param xml_doc: xml document object as provided by a XML parser,
        must implement seishub.util.xml.IXmlDoc
        """

    def getResourceType(): #@NoSelf
        """
        The resource type is determined by the root node of the underlying 
        XML document
        @return: resource type (string)
        """

    def setData(xml_data): #@NoSelf
        """
        @param xml_data: raw xml data
        @type xml_data: string
        """

    def getData(): #@NoSelf
        """
        @return: xml data (string)
        """


class IIndexBase(Interface):
    """
    Base class for index interfaces
    """
    def init(value_path=None, key_path=None, type="text"): #@NoSelf
        pass

    def getKey_path(): #@NoSelf
        """
        @return: key path
        """

    def getValue_path(): #@NoSelf
        """
        @return: value path
        """

    def getType(): #@NoSelf
        """
        @return: data type of the index key
        """

    def getValues(): #@NoSelf
        """
        @return: values of this index
        """


class IXmlIndex(IIndexBase):
    """
    Marker interface for xmldb XML indexes.
    
    An XmlIndex is used in order to index data stored inside a XmlResource's
    XML structure
    """

    def eval(xml_resource): #@NoSelf
        """
        Evaluate this index on a given XmlResource

        @param xml_resource: xmldb.xmlresource.XmlResource object
        @return: list with key, value pairs on success, None else
        """


class IXPathQuery(Interface):
    """
    Marker interface for xmldb xpath query objects.
    """
    def init(query, order_by=None, limit=None): #@NoSelf
        """
        @param param: XPath query
        @type query: string
        @param order_by: list of order by clauses of the form: 
        [["/somenode/someelement/@someattribute" (, "ASC"|"DESC")], 
        ...]
        @type order_by: python list
        @param limit: maximum number of results
        @type limit: int
        """

    def getPredicates(): #@NoSelf
        """
        Get parsed predicates
        @return: parsed predicate expression
        @rtype: L{seishub.xmldb.xpath.PredicateExpression}
        """

    def getValue_path(): #@NoSelf
        """
        Get value path
        @return: value path this query corresponds to
        @rtype: string
        """

    def has_predicates(): #@NoSelf
        """
        @return: True if query has predicates
        @rtype: True | False
        """

    def getOrder_by(): #@NoSelf
        """
        @return: List of parsed order by clauses
        @rtype: python list
        """

    def getLimit(): #@NoSelf
        """
        @return: Result set limit (maximum number of results)
        @rtype: integer
        """
