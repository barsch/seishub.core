# -*- coding: utf-8 -*-

import os

from seishub.core import Component, implements
from seishub.services.interfaces import IPackage, ISchemas, IAliases


class QuakeMLPackage(Component):
    """QuakeML package for SeisHub."""
    implements(IPackage, ISchemas, IAliases)
    
    package_id = 'quakeml'
    
    def getSchemas(self):
        """Package validation schemas."""
        return ['xml' + os.sep + 'QuakeML-BED-1.0.1.xsd', 
                'xml' + os.sep + 'QuakeML-RT-BED-1.0.1.xsd']

    def getAliases(self):
        """Package aliases."""
        return {'lastevents': "/event?order_by=['/quakeml/event/year']/&limit=20",
                'historical-events': "/event?order_by=['/year']/&limit=50",}
