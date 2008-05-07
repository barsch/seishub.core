# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.interfaces import IPackage


class XSeedPackage(Component):
    """XML SEED package for SeisHub."""
    implements(IPackage)
    
    package_id = 'xseed'
    
    def getPackageId(self):
        return 'xseed'
