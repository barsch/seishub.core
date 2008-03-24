from seishub.core import SeisHubError

class InvalidUriError(SeisHubError):
    """raised whenever URI validation fails"""

class UnknownUriError(SeisHubError):
    """raised, if the URI is not known within the storage"""
    
class InvalidIndexError(SeisHubError):
    """raised when trying to create an XmlIndex with invalid args"""
    
class InvalidQueryError(SeisHubError):
    """invalid parameters passed to catalogue's query method"""
    
class AddResourceError(SeisHubError):
    """adding a new resource failed"""
    
class DeleteResourceError(SeisHubError):
    """deleting a resource failed"""
    
class RestrictedXpathError(SeisHubError):
    """invalid restricted xpath expression, 
    @see: L{seishub.xmldb.xpath}"""
    
class InvalidXpathQuery(SeisHubError):
    """invalid query expression"""


class XmlDbManagerError(SeisHubError):
    """general xmldb error"""

class DbError(SeisHubError):
    """general db error"""

class XmlIndexError(SeisHubError):
    """general XmlIndex error"""

class XmlIndexCatalogError(SeisHubError):
    """general XmlIndexCatalog error"""

class XmlResourceError(SeisHubError):
    """general XMlResource error"""
    
class QueryAliasError(SeisHubError):
    """general QueryAlias error"""