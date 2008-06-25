# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminTheme


class DefaultTheme(Component):
    """WebAdmin default theme."""
    implements(IAdminTheme)
    
    def getThemeId(self):
        return ('default', '/css/default.css')


class MagicTheme(Component):
    """New *magic* WebAdmin theme."""
    implements(IAdminTheme)
    
    def getThemeId(self):
        return ('magic', '/css/magic.css')