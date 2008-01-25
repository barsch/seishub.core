# -*- coding: utf-8 -*-

from seishub.core import Interface


class IAdminPanel(Interface):
    """Extension point for adding panels to the administration interface."""
    
    def getPanelId():
        """Return a list of available admin panels.
        
        The items returned by this function must be tuples of the form
        `(category, category_label, page, page_label)`.
        """
    
    def renderPanel(self, request):
        """Process a request for an admin panel.
        
        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template in form of a dictionary.
        """
    
    def getHtdocsDirs():
        """Return a list of directories with static resources (such as style
        sheets, images, etc.).
        
        Each item in the list must be a `(prefix, abspath)` tuple. The
        `prefix` part defines the path in the URL that requests to these
        resources are prefixed with.
        
        The `abspath` is the absolute path to the directory containing the
        resources on the local file system.
        """
    
    def getTemplatesDirs():
        """Return a list of directories containing template files."""