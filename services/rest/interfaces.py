# -*- coding: utf-8 -*-

from seishub.core import Interface


class IUrlMapping(Interface):
    """Extension point for adding URL mappings for the REST service."""
    
    def getUrl():
        """
        Defines the mapped URL for this plugin.
        
        The items should return a single URL string starting with an slash.
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

