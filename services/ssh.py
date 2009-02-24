# -*- coding: utf-8 -*-
"""
A SSH server.
"""
from seishub import __version__ as SEISHUB_VERSION
from seishub.config import IntOption, Option, BoolOption
from seishub.core import PackageManager
from seishub.defaults import SSH_PORT, SSH_PRIVATE_KEY, SSH_PUBLIC_KEY, \
    SSH_AUTOSTART
from seishub.exceptions import SeisHubError
from seishub.packages.interfaces import ISSHCommand
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.conch import avatar, recvline
from twisted.conch.insults import insults
from twisted.conch.interfaces import IConchUser, ISession
from twisted.conch.ssh import factory, keys, session
from twisted.cred import portal
from twisted.python import components
from zope.interface import implements
import os


__all__ = ['SSHService']


class SSHServiceProtocol(recvline.HistoricRecvLine):
    
    def __init__(self, avatar):
        recvline.HistoricRecvLine.__init__(self)
        self.user = avatar
        self.env = avatar.env
        self.status = {}
        plugins = PackageManager.getComponents(ISSHCommand, None, self.env)
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
    
    def characterReceived(self, ch, mch):
        if self.mode == 'insert':
            self.lineBuffer.insert(self.lineBufferIndex, ch)
        else:
            self.lineBuffer[self.lineBufferIndex:self.lineBufferIndex+1] = [ch]
        self.lineBufferIndex += 1
        if 'hide' not in self.status:
            self.terminal.write(ch)
    
    def lineReceived(self, line):
        # check for any internal status
        if self.status:
            cmd = self.status.get('cmd', '')
            try:
                func = getattr(self, 'cmd_' + cmd, None)
                func(line)
            except Exception, e:
                self.writeln("Error: %s" % e)
            return
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
            if not self.status:
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
    
    def handle_RETURN(self):
        if self.lineBuffer and 'hide' not in self.status:
            self.historyLines.append(''.join(self.lineBuffer))
        self.historyPosition = len(self.historyLines)
        line = ''.join(self.lineBuffer)
        self.lineBuffer = []
        self.lineBufferIndex = 0
        self.terminal.nextLine()
        self.lineReceived(line)
    
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
        """
        Prints the current SeisHub version.
        """
        self.writeln('SeisHub SSH version %s' % SEISHUB_VERSION)
    
    def cmd_WHOAMI(self):
        """
        Prints your user name.
        """
        self.writeln(self.user.username)
    
    def cmd_EXIT(self):
        """
        Ends your session.
        """
        self.cmd_QUIT()
    
    def cmd_QUIT(self):
        """
        Ends your session.
        """
        self.writeln("Bye!")
        self.terminal.loseConnection()
    
    def cmd_CLEAR(self):
        """
        Clears the screen.
        """
        self.terminal.reset()
    
    def cmd_PASSWD(self, line=''):
        """
        Changes your password.
        """
        uid = self.user.username
        status = self.status.get('cmd','')
        current = 'current' in self.status
        password = self.status.get('password','')
        if not status:
            # start
            self.writeln("Changing password for %s" % uid)
            self.write("Enter current password: ")
            self.status = dict(cmd='PASSWD', current='', hide=True)
        elif current:
            # test current password
            if not self.env.auth.checkPassword(uid, line):
                # clean up and exit
                self.status = {}
                self.writeln("Authentication failure.")
                self.showPrompt()
            else:
                # prompt for new password
                self.write("Enter new password: ")
                self.status = dict(cmd='PASSWD', password='', hide=True)
        elif password=='':
            # got one new password - ask for confirmation
            self.write("Retype new password: ")
            self.status = dict(cmd='PASSWD', password=line, hide=True)
        elif password!='':
            # ok, got both password - check them
            if password!=line:
                self.writeln("Sorry, passwords do not match.")
            else:
                try:
                    self.env.auth.changePassword(uid, password)
                except SeisHubError(), e:
                    self.writeln(e.message)
                except Exception ,e:
                    raise e
                else:
                    self.writeln("Password has been changed.")
            # clean up and exit
            self.status = {}
            self.showPrompt()


class SSHServiceSession:
    
    def __init__(self, avatar):
        self.avatar = avatar
    
    def getPty(self, term, windowSize, attrs):
        pass
    
    def execCommand(self, proto, cmd):
        raise NotImplementedError
    
    def openShell(self, protocol):
        serverProtocol = insults.ServerProtocol(SSHServiceProtocol, 
                                                self.avatar)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))
    
    def eofReceived(self):
        pass
    
    def closed(self):
        pass
    
    def windowChanged(self, windowSize):
        pass


class SFTPServiceAvatar(avatar.ConchUser):
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({"session": session.SSHSession})

components.registerAdapter(SSHServiceSession, SFTPServiceAvatar, ISession)


class SSHServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            logout = lambda: None
            return IConchUser, SFTPServiceAvatar(avatarId, self.env), logout
        else:
            raise Exception("No supported interfaces found.")


class SSHServiceFactory(factory.SSHFactory):
    """
    Factory for SSH Server.
    """
    def __init__(self, env):
        self.env = env
        self.portal = portal.Portal(SSHServiceRealm(env), 
                                    env.auth.getCheckers())
        #set keys
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}
    
    
    def _getCertificates(self):
        """
        Fetch SSH certificate paths from configuration.
        
        return: Paths to public and private key files.
        """
        pub_file = self.env.config.get('ssh', 'public_key_file')
        priv_file = self.env.config.get('ssh', 'private_key_file')
        if not os.path.isabs(pub_file):
            pub_file = os.path.join(self.env.config.path, pub_file)
        if not os.path.isabs(priv_file):
            priv_file = os.path.join(self.env.config.path, priv_file)
        # test if certificates exist
        msg = "SSH certificate file %s is missing!" 
        if not os.path.isfile(pub_file):
            self.env.log.warn(msg % pub_file)
            return self._generateCertificates()
        if not os.path.isfile(priv_file):
            self.env.log.warn(msg % priv_file)
            return self._generateCertificates()
        return pub_file, priv_file
    
    def _generateCertificates(self):
        """
        Generates new private RSA keys for the SFTP service.
        
        return: Paths to public and private key files.
        """
        from Crypto.PublicKey import RSA
        from twisted.python.randbytes import secureRandom
        # get default path
        pub_file = os.path.join(self.env.config.path, SSH_PUBLIC_KEY)
        priv_file = os.path.join(self.env.config.path, SSH_PRIVATE_KEY)
        # generate
        msg = "Generating new certificate files for the SSH service ..."
        self.env.log.warn(msg)
        rsa_key = RSA.generate(1024, secureRandom)
        # public key
        pub_key = keys.Key(rsa_key).public().toString('openssh')
        file(pub_file, 'w+b').write(str(pub_key))
        msg = "Private key file %s has been created."
        self.env.log.warn(msg % pub_file)
        # private key
        priv_key = keys.Key(rsa_key).toString('openssh')
        file(priv_file, 'w+b').write(str(priv_key))
        msg = "Private key file %s has been created."
        self.env.log.warn(msg % priv_file)
        # write config
        self.env.config.set('ssh', 'public_key_file', pub_file)
        self.env.config.set('ssh', 'private_key_file', priv_file)
        self.env.config.save()
        return pub_file, priv_file


class SSHService(TCPServer): 
    """
    Service for SSH server.
    """
    service_id = "ssh"
    
    BoolOption('ssh', 'autostart', SSH_AUTOSTART, "Run service on start-up.")
    IntOption('ssh', 'port', SSH_PORT, "SSH port number.")
    Option('ssh', 'public_key_file', SSH_PUBLIC_KEY, "Public RSA key.")
    Option('ssh', 'private_key_file', SSH_PRIVATE_KEY, "Private RSA key.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('ssh', 'port')
        TCPServer.__init__(self, port, SSHServiceFactory(env))
        self.setName("SSH")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('ssh', 'autostart'):
            TCPServer.privilegedStartService(self)
    
    def startService(self):
        if self.env.config.getbool('ssh', 'autostart'):
            TCPServer.startService(self)
