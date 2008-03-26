# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.services.rest.interfaces import IRESTProcessor
from seishub.services.rest.alias import registerAlias


registerAlias('/lastevents', 'quakeml', "/event?order_by=['/quakeml/event/year']/&limit=20")
registerAlias('/historical-events', 'quakeml', '/event', 
              order_by = ['/year'], limit = 50)


class QuakeML101Processor(Component):
    """QuakeML 1.0.1 plugin for the REST service."""
    implements(IRESTProcessor)
    
    def getProcessorId(self):
        return ('quakeml101', '/quakeml/1.0.1', 'publicId')
    
    def getSchemata(self):
        return ['QuakeML-BED-1.0.1.xsd']
    
    def processPUT(self, request):
        return 'uploaded'


class QuakeMLRealTime101Processor(Component):
    """QuakeML RT 1.0.1 plugin for the REST service."""
    implements(IRESTProcessor)
    
    def getProcessorId(self):
        return ('quakemlrt101', '/quakemlrt/1.0.1', 'publicId')
    
    def getSchemata(self):
        return ['QuakeML-RT-BED-1.0.1.xsd']
    
    def processGET(self, request):
        return 'geht'
    
    def processPUT(self, request):
        return 'uploaded'


#class CombinedQuakeMLProcessor(QuakeML11Processor):
#    """Central QuakeML plug-in handles QuakeML 1.0 and 1.1 GET requests."""
#    implements(IRESTProcessor)
#    
#    def getIds(self):
#        return ('quakeml', '/quakeml', 'publicId')
#    
#    def processGET(self, request):
#        # if quakeml10 -> use QuakeML10_to_11 XSLT
#        # else quakeml11 -> use QuakeML11 XSLT
#        return 'geht'

