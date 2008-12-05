# -*- coding: utf-8 -*-
"""
A SFTP server.
"""

from seishub.config import IntOption, Option, BoolOption
from seishub.defaults import SFTP_AUTOSTART, SFTP_PORT, SFTP_PRIVATE_KEY, \
    SFTP_PUBLIC_KEY, SFTP_LOG_FILE
from seishub.services.sftp.protocol import SFTPServiceProtocol
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.conch import avatar
from twisted.conch.interfaces import ISFTPServer, IConchUser
from twisted.conch.ssh import factory, keys, session, filetransfer
from twisted.cred import portal
from twisted.python import components
from zope.interface import implements
import os


class SFTPServiceAvatar(avatar.ConchUser):
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({"session": session.SSHSession})
        self.subsystemLookup.update({"sftp": filetransfer.FileTransferServer})

components.registerAdapter(SFTPServiceProtocol, SFTPServiceAvatar, ISFTPServer)


class SFTPServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
            logout = lambda: None
            return IConchUser, SFTPServiceAvatar(avatarId, self.env), logout
        else:
            raise Exception, "No supported interfaces found."


class SFTPServiceFactory(factory.SSHFactory):
    """
    Factory for SFTP server.
    """
    def __init__(self, env):
        self.env = env
        self.portal = portal.Portal(SFTPServiceRealm(env), 
                                    env.auth.getCheckers())
        #set keys
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}
        # log file
        log_file = env.config.get('sftp', 'log_file') or None
        if not os.path.isabs(log_file):
            log_file = os.path.join(self.env.config.path, log_file)
    
    def _getCertificates(self):
        """
        Fetch SFTP certificate paths from configuration.
        
        return: Paths to public and private key files.
        """
        pub_file = self.env.config.get('sftp', 'public_key_file')
        priv_file = self.env.config.get('sftp', 'private_key_file')
        if not os.path.isabs(pub_file):
            pub_file = os.path.join(self.env.config.path, pub_file)
        if not os.path.isabs(priv_file):
            priv_file = os.path.join(self.env.config.path, priv_file)
        # test if certificates exist
        msg = "SFTP certificate file %s is missing!" 
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
        pub_file = os.path.join(self.env.config.path, SFTP_PUBLIC_KEY)
        priv_file = os.path.join(self.env.config.path, SFTP_PRIVATE_KEY)
        # generate
        msg = "Generating new certificate files for the SFTP service ..."
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
        self.env.config.set('sftp', 'public_key_file', pub_file)
        self.env.config.set('sftp', 'private_key_file', priv_file)
        self.env.config.save()
        return pub_file, priv_file


class SFTPService(TCPServer):
    """
    Service for SFTP server.
    """
    BoolOption('sftp', 'autostart', SFTP_AUTOSTART, 'Run service on start-up.')
    IntOption('sftp', 'port', SFTP_PORT, "SFTP port number.")
    Option('sftp', 'public_key_file', SFTP_PUBLIC_KEY, 'Public RSA key.')
    Option('sftp', 'private_key_file', SFTP_PRIVATE_KEY, 'Private RSA key.')
    Option('sftp', 'log_file', SFTP_LOG_FILE, "SFTP access log file.")
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('sftp', 'port')
        TCPServer.__init__(self, port, SFTPServiceFactory(env))
        self.setName("SFTP")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('sftp', 'autostart'):
            TCPServer.privilegedStartService(self)
    
    def startService(self):
        if self.env.config.getbool('sftp', 'autostart'):
            TCPServer.startService(self)
