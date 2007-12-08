from zope.interface import implements

from seishub.interfaces import IAdminPanel
from seishub.core import Component

class BasicsPanel(Component):
    implements(IAdminPanel)