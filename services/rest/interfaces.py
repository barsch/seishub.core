# -*- coding: utf-8 -*-

from seishub.core import Interface


class IRESTMapper(Interface):
    """Extension point for adding URL mappings for the REST service."""
    
    def getProcessorId():
        """
        Defines the root URL, package ID and the resource identifier attribute 
        for this REST plugin.
        
        The items should return a tuple with a unique package id, the mapped
        root URL starting with an slash and the attribute name of the resource 
        identifier.
        """
    
    def processGET(request):
        """
        Process a GET request.
        
        This function should return a string containing a valid XML document.
        """
    
    def processPUT(request):
        """
        Process a PUT request.
        
        This function should return a string containing the new resource url.
        """
    
    def processPOST(request):
        """
        Process a POST request.
        
        This function should return a string containing the new resource url if
        the resource could be updated, otherwise a SeisHubError instance.
        """
    
    def processDELETE(request):
        """
        Process a DELETE request.
        
        This function should return True if the resource could be deleted 
        otherwise a SeisHubError instance.
        """