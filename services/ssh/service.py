# -*- coding: utf-8 -*-

import os

from zope.interface import implements
from twisted.cred import portal, checkers
from twisted.conch import recvline, avatar, interfaces as conchinterfaces
from twisted.conch.ssh import factory, keys, session, common
from twisted.conch.insults import insults
from twisted.application import internet

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
        self.plugin_cmds = dict([(p.getCommandId(), p) 
                                 for p in plugins 
                                 if hasattr(p, 'executeCommand')
                                 and hasattr(p, 'getCommandId')])
        self.buildin_cmds = [f[3:] for f in dir(self) if f.startswith('do_')]
    
    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        self.terminal.write("Welcome to SeisHub " + SEISHUB_VERSION)
        self.terminal.nextLine()
        self.showPrompt()
    
    def showPrompt(self):
        self.terminal.write("$ ")
    
    def lineReceived(self, line):
        line = line.strip()
        if not line:
            self.showPrompt()
            return
        cmd_and_args = line.split()
        cmd = cmd_and_args[0]
        args = cmd_and_args[1:]
        if cmd in self.buildin_cmds:
            try:
                func = getattr(self, 'do_' + cmd, None)
                func(*args)
            except Exception, e:
                self.terminal.write("Error: %s" % e)
                self.terminal.nextLine()
        elif cmd in self.plugin_cmds.keys():
            ssh_cmd = self.plugin_cmds.get(cmd)
            for l in ssh_cmd.executeCommand(args):
                self.terminal.write(l)
                self.terminal.nextLine()
        else:
            self.terminal.write("No such command: " + cmd)
            self.terminal.nextLine()
            self.terminal.write("Use help to get all available commands.")
            self.terminal.nextLine()
            
        self.showPrompt()
    
    def do_help(self, *args):
        self.terminal.write('== Build-in keywords ==')
        self.terminal.nextLine()
        for cmd in self.buildin_cmds:
            func = getattr(self, 'do_' + cmd, None)
            func_doc = func.__doc__
            if not func_doc:
                continue
            self.terminal.write(cmd + ' - ' + str(func_doc))
            self.terminal.nextLine()
        self.terminal.nextLine()
        self.terminal.write('== Plugin keywords ==')
        self.terminal.nextLine()
        for cmd, plugin in self.plugin_cmds.items():
            self.terminal.write(cmd + ' - ' + str(plugin.__doc__))
            self.terminal.nextLine()
    
    def do_version(self):
        """Prints the current SeisHub version."""
        self.terminal.write(SEISHUB_VERSION)
        self.terminal.nextLine()
    
    def do_whoami(self):
        """Prints your user name."""
        self.terminal.write(self.user.username)
        self.terminal.nextLine()
    
    def do_exit(self):
        """Ends your session."""
        self.do_quit()
    
    def do_quit(self):
        """Ends your session."""
        self.terminal.write("Bye!")
        self.terminal.nextLine()
        self.terminal.loseConnection()
    
    def do_clear(self):
        """Clears the screen."""
        self.terminal.reset()


class SSHServiceAvatar(avatar.ConchUser):
    implements(conchinterfaces.ISession)
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({'session': session.SSHSession})
    
    def openShell(self, protocol):
        serverProtocol = insults.ServerProtocol(SSHServiceProtocol, self, self.env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))
    
    def getPty(self, terminal, windowSize, attrs):
        return None
    
    def execCommand(self, protocol, cmd):
        raise NotImplementedError
    
    def closed(self):
        pass


class SSHServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if conchinterfaces.IConchUser in interfaces:
            return interfaces[0], SSHServiceAvatar(avatarId, self.env), lambda: None
        else:
            raise Exception, "No supported interfaces found."


class SSHServiceFactory(factory.SSHFactory):
    """Factory for SSH Server."""
    
    def __init__(self, env):
        self.env = env
        users = {'admin': 'aaa', }
        realm = SSHServiceRealm(env)
        check = [checkers.InMemoryUsernamePasswordDatabaseDontUse(**users)]
        self.portal = portal.Portal(realm, check)
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        
        pub = self.env.config.get('ssh', 'public_key_file')
        priv = self.env.config.get('ssh', 'private_key_file')
        if not os.path.isfile(pub):
            pub = os.path.join(self.env.path, 'conf', pub)
            if not os.path.isfile(pub):
                self._generateRSAKeys()
        if not os.path.isfile(priv):
            priv = os.path.join(self.env.path, 'conf', priv)
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
        pub = os.path.join(self.env.path, 'conf', SSH_PUBLIC_KEY)
        priv = os.path.join(self.env.path, 'conf', SSH_PRIVATE_KEY)
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
