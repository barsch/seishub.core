# -*- coding: utf-8 -*-

from zope.interface import Interface


class IResource(Interface):
    """A basic resource consist at least of an unique uri and optionally of
    any kinds of data
    """
    def getUri(self):
        """retrieve the resource's uri """
        
    def setUri(self,newuri):
        """change resource's uri attribute
        a resource cannot be serialized without specifying an uri
        """
        
    def setData(self,newdata):
        """set data attribute"""
        
    def getData(self):
        """retrieve the resource's data"""
        
    