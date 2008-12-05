# -*- coding: utf-8 -*-
"""
Administrative resources.
"""

from seishub.core import ExtensionPoint
from seishub.exceptions import NotImplementedError, SeisHubError
from seishub.processor.resources.resource import Resource, StaticFolder
from seishub.processor.interfaces import IAdminPanel, IAdminTheme
from twisted.web import http


class AdminResource(Resource):
    """
    Processor handler of a mapping folder.
    """
    def __init__(self, mapper, folderish=True, category='admin'):
        Resource.__init__(self)
        self.is_leaf = True
        self.mapper = mapper
        self.category = category
        self.folderish = folderish
    
    def render_GET(self, request):
        return ''
    
    def render_POST(self, request):
        return ''
    
    def _clone(self, **kwargs):
        return self.__class__(self.mapper, **kwargs)


class AdminRootFolder(StaticFolder):
    """
    The root folder resource containing all active administrative resources.
    """
    def __init__(self):
        Resource.__init__(self)
        self.category = 'folder'
    
    def render_GET(self, request):
        """
        Returns content of this folder node as dictionary.
        """
        themes = ExtensionPoint(IAdminTheme).extensions(request.env)
        print [p for p in themes if hasattr(p, 'theme_id')]
        return "%s " % (themes)
