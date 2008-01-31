# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.core import Component, implements
from seishub.services.telnet.interfaces import ITelnetCmd


class ServicesCmd(Component):
    """Telnet command to handle services."""
    implements(ITelnetCmd)
    
    def getCommandId(self):
        return 'services'
    
    def executeCommand(self, args):
        services = service.IServiceCollection(self.env.app)
        data = []
        for s in services:
            data.append(s.name + ' ' + str(s.running))
        return data