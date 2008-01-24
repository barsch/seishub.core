# -*- coding: utf-8 -*-

from seishub.core import Interface


class IAdminPanel(Interface):
    """Extension point interface for adding panels to the web-based
    administration interface.
    """

    def getPanelId():
        """Return a tuple of the available admin panel id and name.
        
        The item returned by this function must be a tuple of the form
        `(page, page_label)`.
        """

    def renderPanel(self, request):
        """Process a request for an admin panel.
        
        This function should return a dict with the following keys:
        template, data and status.
        """
    
    def getHtdocsDirs():
        """Return a list of directories with static resources (such as style
        sheets, images, etc.)
        
        Each item in the list must be a `(prefix, abspath)` tuple. The
        `prefix` part defines the path in the URL that requests to these
        resources are prefixed with.
        
        The `abspath` is the absolute path to the directory containing the
        resources on the local file system.
        """
    
    def getTemplatesDirs():
        """Return a list of directories containing template files."""