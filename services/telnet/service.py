# -*- coding: utf-8 -*-

from twisted.internet import protocol
from twisted.protocols import basic

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.telnet.interfaces import ITelnetCmd
from seishub.core import ExtensionPoint
from seishub.util.text import getTextUntilDot


class TelnetLineReciever(basic.LineReceiver):
    def __init__(self):
        telnet_plugins = ExtensionPoint(ITelnetCmd).extensions(self.env)
        self.telnet_cmds = dict([(p.getCommandId(),p) 
                                 for p in telnet_plugins 
                                 if hasattr(p, 'executeCommand')
                                 and hasattr(p, 'getCommandId')]) 
    
    def lineReceived(self, line):
        # XXX: not very clean
        line = line.strip()
        line = line.replace('  ',' ')
        line = line.replace('  ',' ')
        splitline = line.split(' ')
        if line == 'quit':
            self._out("Bye!")
            self.transport.loseConnection()
        elif line == 'version':
            self._out(SEISHUB_VERSION)
        elif line == 'help':
            for keyword, plugin in self.telnet_cmds.items():
                self._out(keyword+' - '+getTextUntilDot(plugin.__doc__))
        elif splitline[0] in self.telnet_cmds.keys():
            cmd = self.telnet_cmds.get(splitline[0])
            for l in cmd.executeCommand(splitline):
                self._out(l)
        else:
            self._out("Unknown keyword: " + line)
            self._out("Use help to get a list of all available commands.")
    
    def _out(self, line):
        self.sendLine('> ' + str(line))

class TelnetService(protocol.ServerFactory):
    """Factory for HTTP Server."""
    protocol = TelnetLineReciever
    
    def __init__(self, env):
        self.env = env
        self.protocol.env = env
