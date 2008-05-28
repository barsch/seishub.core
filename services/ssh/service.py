# -*- coding: utf-8 -*-

import os

from zope.interface import implements
from twisted.cred import portal
from twisted.conch import recvline, avatar, interfaces as conchinterfaces
from twisted.conch.ssh import factory, keys, common, session
from twisted.conch.insults import insults
from twisted.application import internet
from twisted.internet import threads

from seishub import __version__ as SEISHUB_VERSION
from seishub.services.ssh.interfaces import ISSHCommand
from seishub.core import ExtensionPoint
from seishub.defaults import SSH_PORT, SSH_PRIVATE_KEY, SSH_PUBLIC_KEY
from seishub.config import IntOption, Option


class SSHServiceProtocol(recvline.HistoricRecvLine):
    
    def __init__(self, user, env):
        recvline.HistoricRecvLine.__init__(self)
        self.env = env
        self.user = user
        plugins = ExtensionPoint(ISSHCommand).extensions(self.env)
        self.plugin_cmds = dict([(p.getCommandId().upper(), p) 
                                 for p in plugins 
                                 if hasattr(p, 'executeCommand')
                                 and hasattr(p, 'getCommandId')])
        self.buildin_cmds = [f[4:].upper() for f in dir(self) \
                             if f.startswith('cmd_')]
    
    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        self.writeln("Welcome to SeisHub " + SEISHUB_VERSION)
        self.showPrompt()
    
    def showPrompt(self):
        self.write("$ ")
    
    def lineReceived(self, line):
        line = line.strip()
        if not line:
            self.showPrompt()
            return
        cmd_and_args = line.split()
        cmd = cmd_and_args[0].upper()
        args = cmd_and_args[1:]
        # check if its a build-in command
        if cmd in self.buildin_cmds:
            try:
                func = getattr(self, 'cmd_' + cmd, None)
                func(*args)
            except Exception, e:
                self.writeln("Error: %s" % e)
            self.showPrompt()
            return
        # check if its a user defined command
        # XXX: Thread is not working here!!!!
        if cmd in self.plugin_cmds.keys():
            ssh_cmd = self.plugin_cmds.get(cmd)
            for l in ssh_cmd.executeCommand(args):
                self.writeln(l)    
        else:
            # command not known
            self.writeln("No such command: " + cmd)
            self.writeln("Use help to get all available commands.")
        self.showPrompt()
        return
    
    def write(self, data):
        self.terminal.write(data)
    
    def writeln(self, data):
        self.write(data)
        self.nextLine()
    
    def nextLine(self):
        self.write('\r\n')
    
    def cmd_HELP(self, *args):
        self.writeln('== Build-in keywords ==')
        for cmd in self.buildin_cmds:
            func = getattr(self, 'cmd_' + cmd, None)
            func_doc = func.__doc__
            if not func_doc:
                continue
            self.writeln(cmd + ' - ' + str(func_doc))
        self.nextLine()
        self.writeln('== Plugin keywords ==')
        for cmd, plugin in self.plugin_cmds.items():
            self.writeln(cmd + ' - ' + str(plugin.__doc__))
    
    def cmd_VERSION(self):
        """Prints the current SeisHub version."""
        self.writeln('SeisHub SSH version %s' % SEISHUB_VERSION)
    
    def cmd_WHOAMI(self):
        """Prints your user name."""
        self.writeln(self.user.username)
    
    def cmd_EXIT(self):
        """Ends your session."""
        self.cmd_QUIT()
    
    def cmd_QUIT(self):
        """Ends your session."""
        self.writeln("Bye!")
        self.terminal.loseConnection()
    
    def cmd_CLEAR(self):
        """Clears the screen."""
        self.terminal.reset()
    
    # XXX: this should be removed in a productive environment
    def cmd_DEBUG(self):
        """Starts debugger."""
        import pdb;pdb.set_trace()


class SSHServiceAvatar(avatar.ConchUser):
    implements(conchinterfaces.ISession)
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({'session': session.SSHSession})
    
    def openShell(self, protocol):
        serverProtocol = insults.ServerProtocol(SSHServiceProtocol, self, 
                                                self.env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))
    
    def getPty(self, terminal, windowSize, attrs):
        pass
    
    def execCommand(self, protocol, cmd):
        raise NotImplementedError
    
    def closed(self):
        pass
    
    def windowChanged(self, windowSize):
        pass
    
    def eofReceived(self):
        pass


class SSHServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if conchinterfaces.IConchUser in interfaces:
            return interfaces[0], SSHServiceAvatar(avatarId, self.env), \
                   lambda: None
        else:
            raise Exception, "No supported interfaces found."


class SSHServiceFactory(factory.SSHFactory):
    """Factory for SSH Server."""
    
    def __init__(self, env):
        self.env = env
        self.portal = portal.Portal(SSHServiceRealm(env), env.auth)
        #set keys
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        
        pub = self.env.config.get('ssh', 'public_key_file')
        priv = self.env.config.get('ssh', 'private_key_file')
        if not os.path.isfile(pub):
            pub = os.path.join(self.env.config.path, 'conf', pub)
            if not os.path.isfile(pub):
                self._generateRSAKeys()
        if not os.path.isfile(priv):
            priv = os.path.join(self.env.config.path, 'conf', priv)
            if not os.path.isfile(priv):
                self._generateRSAKeys()
        return pub, priv
    
    def _generateRSAKeys(self):
        """Generates new private RSA keys for the SSH service."""
        
        print "Generate keys ..."
        from Crypto.PublicKey import RSA
        KEY_LENGTH = 1024
        rsaKey = RSA.generate(KEY_LENGTH, common.entropy.get_bytes)
        publicKeyString = keys.makePublicKeyString(rsaKey)
        privateKeyString = keys.makePrivateKeyString(rsaKey)
        pub = os.path.join(self.env.config.path, 'conf', SSH_PUBLIC_KEY)
        priv = os.path.join(self.env.config.path, 'conf', SSH_PRIVATE_KEY)
        file(pub, 'w+b').write(publicKeyString)
        file(priv, 'w+b').write(privateKeyString)


class SSHService(internet.TCPServer):
    """Service for SSH server."""
    IntOption('ssh', 'port', SSH_PORT, "SSH port number.")
    Option('ssh', 'public_key_file', SSH_PUBLIC_KEY, 'Public RSA key file.')
    Option('ssh', 'private_key_file', SSH_PRIVATE_KEY, 'Private RSA key file.')
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('ssh', 'port')
        internet.TCPServer.__init__(self, port, SSHServiceFactory(env))
        self.setName("SSH")
        self.setServiceParent(env.app)
