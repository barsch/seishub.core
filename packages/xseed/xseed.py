# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage


class XSeedPackage(Component):
    """XML SEED package for SeisHub."""
    implements(IPackage)
    
    def getPackageId(self):
        return ('xseed', '/xseed/', 'publicId')
