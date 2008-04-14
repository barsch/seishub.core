# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.core import Component, implements
from seishub.services.ssh.interfaces import ISSHCommand


class ServicesCommand(Component):
    """SSH command to handle services."""
    implements(ISSHCommand)
    
    def getCommandId(self):
        return 'service'
    
    def executeCommand(self, args):
        services = service.IServiceCollection(self.env.app)
        data = []
        if len(args)==2:
            ENABLE = ['start','enable', 'on']
            DISABLE = ['stop', 'disable', 'off']
            
            srv_name = args[1].lower()
            action = args[0].lower()
            if action in ENABLE:
                self.env.enableService(srv_name)
            elif action in DISABLE:
                self.env.disableService(srv_name)
        RUNNING = ['OFF','ON']
        for s in services:
            data.append(s.name + ' ' + RUNNING[s.running])
        return data