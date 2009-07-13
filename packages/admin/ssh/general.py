# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.packages.interfaces import ISSHCommand
from twisted.application import service


class ServiceCommand(Component):
    """
    Start/stop services.
    """
    implements(ISSHCommand)

    def getCommandId(self):
        return 'service'

    def executeCommand(self, request, args):
        services = service.IServiceCollection(self.env.app)
        if len(args) == 2:
            ENABLE = ['start', 'enable', 'on']
            DISABLE = ['stop', 'disable', 'off']
            srv_name = args[1].lower()
            action = args[0].lower()
            if action in ENABLE:
                self.env.enableService(srv_name)
            elif action in DISABLE:
                self.env.disableService(srv_name)
        RUNNING = ['OFF', 'ON']
        for s in services:
            request.writeln(s.name + ' ' + RUNNING[s.running])


class ReindexCommand(Component):
    """
    Reindex the catalog (takes quite a while and blocks the server).
    """
    implements(ISSHCommand)

    def getCommandId(self):
        return 'reindex'

    def executeCommand(self, request, args):
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        for pid, rid_list in resourcetypes.iteritems():
            for rid in rid_list:
                try:
                    self.env.catalog.reindexResourceType(package_id=pid,
                                                         resourcetype_id=rid)
                except Exception, e:
                    self.log.error("Error reindexing all resources", e)
                    request.writeln("Error reindexing %s/%s" % (pid, rid))
                else:
                    request.writeln("%s/%s has been reindexed." % (pid, rid))
