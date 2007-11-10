# -*- coding: utf-8 -*-

from zope.interface import Interface

class IXmlResource(Interface):
    """XmlResource is a subclass of Resource providing some special xml 
    functionality such as xml validation and parsing
    """
    pass


class IXmlStorageManager(Interface):
    """Basic XML Storage Manager Description"""
    
    def addResource(self,xmlResource):
        """Add a new resource to the storage"""
        
    def updateResource(self,xmlResource):
        """Update an existing resource"""
        
    def deleteResource(self,URI):
        """Delete an existing resource"""
        
    def getResource(self,URI):
        """Retreive an existing resource from the storage"""
        
    def query(self,query_str):
        """Query the storage"""