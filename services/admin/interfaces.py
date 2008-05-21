# -*- coding: utf-8 -*-

from seishub.core import Interface


class IAdminPanel(Interface):
    """Extension point for adding panels to the administration interface."""
    
    def getPanelId():
        """
        Defines ids and labels of this admin panel.
        
        The items returned by this function must be tuples of the form
        `(category, category_label, page, page_label)`.
        """
    
    def renderPanel(request):
        """
        Process a request for an admin panel.
        
        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template in form of a dictionary.
        """
    
    def getHtdocsDirs():
        """
        Return a dict of static resources (such as css files, images, etc.).
        
        Each entry consists of a 'prefix' and an 'abspath'. The 'prefix' part 
        defines the full path that requests to these resources are prefixed 
        with, e.g. '/images/test.jpg'.
        
        The 'abspath' is the absolute path to the directory containing the
        resources on the local file system.
        """
    
    def getTemplatesDirs():
        """Return a list of directories containing template files."""
