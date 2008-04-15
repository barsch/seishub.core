# -*- coding: utf-8 -*-

from seishub.core import Interface


class IPackage(Interface):
    """This is the main interface for a unique seishub package."""
    
    def getPackageId():
        """
        Defines the root URL, package ID and the resource identifier attribute 
        for this package.
        
        The items should return a tuple with a unique package id, the mapped
        root URL starting with an slash and the attribute name of the resource 
        identifier.
        """


class IXMLStylesheet(Interface):
    """Interface of a SeisHub package."""
    
    def getStylesheets():
        """
        Return dict of output stylesheets in form of {'output_id': 'URI',}.
        """


class IXMLSchema(Interface):
    """Extension point for adding URL mappings for the REST service."""
    
    def getSchemas():
        """
        Return URI list of validation schemas (dtd or xsd).
        """