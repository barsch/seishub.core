# -*- coding: utf-8 -*-

import os

from zope.interface import implements
from twisted.cred import portal, checkers
from twisted.conch.ssh import factory, keys, common
from twisted.application import internet
from twisted.conch.interfaces import IConchUser
from twisted.protocols.ftp import IFTPShell

from seishub import __version__ as SEISHUB_VERSION
from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY
from seishub.config import IntOption, Option

from seishub.services.sftp import inmem
from seishub.services.sftp import sftp
from seishub.services.sftp import pathutils


class SFTPServiceRealm(object):
    implements(portal.IRealm)
    
    def __init__(self, vfs, env):
        """
        @param vfs: an implementation of ivfs.IFileSystemContainer.
        """
        self.env = env
        self.vfs = vfs
    
    def requestAvatar(self, username, mind, *interfaces):
        for interface in interfaces:
            # sftp user
            if interface is IConchUser:
                user = sftp.VFSConchUser(username, self.vfs)
                return interface, user, user.logout

            # ftp user
            elif interface is IFTPShell:
                return (
                    interface,
                    IFTPShell(pathutils.FileSystem(self.vfs)),
                    None,
                )
        raise NotImplementedError("Can't support that interface.")


class SFTPServiceFactory(factory.SSHFactory):
    """Factory for SFTP Server."""
    
    def __init__(self, env):
        self.env = env
        vfs = inmem.FakeDirectory()
        p = portal.Portal(SFTPServiceRealm(vfs, env))
        p.registerChecker(checkers.InMemoryUsernamePasswordDatabaseDontUse(admin='aaa'))
        self.portal = p
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}
    
    def _getCertificates(self):
        """Fetching certificate files from configuration."""
        
        pub = self.env.config.get('sftp', 'public_key_file')
        priv = self.env.config.get('sftp', 'private_key_file')
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
        """Generates new private RSA keys for the SFTP service."""
        
        print "Generate keys ..."
        from Crypto.PublicKey import RSA
        KEY_LENGTH = 1024
        rsaKey = RSA.generate(KEY_LENGTH, common.entropy.get_bytes)
        publicKeyString = keys.makePublicKeyString(rsaKey)
        privateKeyString = keys.makePrivateKeyString(rsaKey)
        pub = os.path.join(self.env.config.path, 'conf', SFTP_PUBLIC_KEY)
        priv = os.path.join(self.env.config.path, 'conf', SFTP_PRIVATE_KEY)
        file(pub, 'w+b').write(publicKeyString)
        file(priv, 'w+b').write(privateKeyString)


class SFTPService(internet.TCPServer):
    """Service for SFTP server."""
    IntOption('sftp', 'port', SFTP_PORT, "SFTP port number.")
    Option('sftp', 'public_key_file', SFTP_PUBLIC_KEY, 'Public RSA key file.')
    Option('sftp', 'private_key_file', SFTP_PRIVATE_KEY, 'Private RSA key file.')
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('sftp', 'port')
        internet.TCPServer.__init__(self, port, SFTPServiceFactory(env))
        self.setName("SFTP")
        self.setServiceParent(env.app)
