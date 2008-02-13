from seishub.core import SeisHubError

class InvalidUriError(SeisHubError):
    pass

class UnknownUriError(SeisHubError):
    pass

class XmlDbManagerError(SeisHubError):
    pass

class DbError(SeisHubError):
    pass

class XmlIndexError(SeisHubError):
    pass

class XmlIndexCatalogError(SeisHubError):
    pass

class InvalidIndexError(SeisHubError):
    pass

class XmlResourceError(SeisHubError):
    pass

class AddResourceError(SeisHubError):
    pass

class DeleteResourceError(SeisHubError):
    pass

class RestrictedXpathError(SeisHubError):
    pass