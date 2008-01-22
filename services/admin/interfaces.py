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

    def renderPanel(request):
        """Process a request for an admin panel.
        
        This function should return a dict with the following keys:
        template, data and status.
        """
