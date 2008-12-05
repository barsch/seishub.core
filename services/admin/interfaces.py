# -*- coding: utf-8 -*-

from seishub.core import Interface
from seishub.processor.interfaces import IAdminPanel, IAdminTheme


class IAdminStaticContent(Interface):
    """Extension point for adding static content to the web-based 
    administration interface."""
    
    def getStaticContent():
        """Return a dict of static resources (such as css files, images, etc.).
        
        Each entry consists of a 'prefix' and an 'abspath'. The 'prefix' part 
        defines the full path that requests to these resources are prefixed 
        with, e.g. '/images/test.jpg'.
        
        The 'abspath' is the absolute path to the directory containing the
        resources on the local file system.""" 
