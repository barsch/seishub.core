# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.rest.interfaces import IRESTMapper
from seishub.services.rest.alias import registerAlias
from seishub.packages.interfaces import IPackage, IXMLSchema


registerAlias('/lastevents', 'quakeml', "/event?order_by=['/quakeml/event/year']/&limit=20")
registerAlias('/historical-events', 'quakeml', '/event', 
              order_by = ['/year'], limit = 50)


class QuakeMLPackage(Component):
    """QuakeML package for SeisHub."""
    implements(IPackage, IXMLSchema)
    
    def getPackageId(self):
        return ('quakeml', '/quakeml/', 'publicId')
    
    def getSchemas(self):
        return ['QuakeML-BED-1.0.1.xsd', 'QuakeML-RT-BED-1.0.1.xsd']
