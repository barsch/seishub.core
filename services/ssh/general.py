# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import defer

from seishub.core import Component, implements
from seishub.services.ssh.interfaces import ISSHCommand


class ServicesCommand(Component):
    """SSH command to handle services."""
    implements(ISSHCommand)
    
    def getCommandId(self):
        return 'services'
    
    def executeCommand(self, args):
        services = service.IServiceCollection(self.env.app)
        data = []
        if len(args)==2:
            ENABLE = ['start','enable', 'on']
            DISABLE = ['stop', 'disable', 'off']
            
            srv_name = args[1].lower()
            action = args[0].lower()
            if action in ENABLE:
                self._enableService(srv_name)
            elif action in DISABLE:
                self._disableService(srv_name)
        for s in services:
            data.append(s.name + ' ' + str(s.running))
        return data
    
    @defer.inlineCallbacks
    def _enableService(self, srv_name):
        for srv in service.IServiceCollection(self.env.app):
            if srv.name.lower()==srv_name.lower():
                yield defer.maybeDeferred(srv.startService)
                self.log.info('Starting service %s' % srv.name)
    
    @defer.inlineCallbacks
    def _disableService(self, srv_name):
        for srv in service.IServiceCollection(self.env.app):
            if srv.name.lower()==srv_name.lower():
                yield defer.maybeDeferred(srv.stopService)
                self.log.info('Stopping service %s' % srv.name)    