# -*- coding: utf-8 -*-
"""
A Manhole server.
"""
from seishub.core.config import IntOption, Option, BoolOption
from seishub.core.defaults import MANHOLE_PORT, MANHOLE_PRIVATE_KEY, \
    MANHOLE_PUBLIC_KEY, MANHOLE_AUTOSTART
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.conch import manhole, manhole_ssh
from twisted.conch.ssh import keys
from twisted.cred import portal
import os


__all__ = ['ManholeService']


class ManholeServiceFactory(manhole_ssh.ConchFactory):
    """
    Factory for Manhole Server.
    """
    def __init__(self, env):
        self.env = env
        realm = manhole_ssh.TerminalRealm()
        namespace = globals()
        namespace['env'] = env
        def getManhole(_):
            return manhole.Manhole(namespace)
        realm.chainedProtocolFactory.protocolFactory = getManhole
        self.portal = portal.Portal(realm, env.auth.getCheckers())
        #set keys
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': keys.Key.fromFile(priv)}


    def _getCertificates(self):
        """
        Fetch Manhole certificate paths from configuration.
        
        return: Paths to public and private key files.
        """
        pub_file = self.env.config.get('manhole', 'public_key_file')
        priv_file = self.env.config.get('manhole', 'private_key_file')
        if not os.path.isabs(pub_file):
            pub_file = os.path.join(self.env.config.path, pub_file)
        if not os.path.isabs(priv_file):
            priv_file = os.path.join(self.env.config.path, priv_file)
        # test if certificates exist
        msg = "Manhole certificate file %s is missing!"
        if not os.path.isfile(pub_file):
            self.env.log.warn(msg % pub_file)
            return self._generateCertificates()
        if not os.path.isfile(priv_file):
            self.env.log.warn(msg % priv_file)
            return self._generateCertificates()
        return pub_file, priv_file

    def _generateCertificates(self):
        """
        Generates new private RSA keys for the Manhole service.
        
        return: Paths to public and private key files.
        """
        from Crypto.PublicKey import RSA
        from twisted.python.randbytes import secureRandom
        # get default path
        pub_file = os.path.join(self.env.config.path, MANHOLE_PUBLIC_KEY)
        priv_file = os.path.join(self.env.config.path, MANHOLE_PRIVATE_KEY)
        # generate
        msg = "Generating new certificate files for the Manhole service ..."
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
        self.env.config.set('manhole', 'public_key_file', pub_file)
        self.env.config.set('manhole', 'private_key_file', priv_file)
        self.env.config.save()
        return pub_file, priv_file


class ManholeService(TCPServer):
    """
    Service for Manhole server.
    """
    service_id = "manhole"

    BoolOption('manhole', 'autostart', MANHOLE_AUTOSTART,
        "Run service on start-up.")
    IntOption('manhole', 'port', MANHOLE_PORT, "Manhole port number.")
    Option('manhole', 'public_key_file', MANHOLE_PUBLIC_KEY, "Public RSA key.")
    Option('manhole', 'private_key_file', MANHOLE_PRIVATE_KEY,
        "Private RSA key.")

    def __init__(self, env):
        self.env = env
        port = env.config.getint('manhole', 'port')
        TCPServer.__init__(self, port, ManholeServiceFactory(env))
        self.setName("Manhole")
        self.setServiceParent(env.app)

    def privilegedStartService(self):
        if self.env.config.getbool('manhole', 'autostart'):
            TCPServer.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('manhole', 'autostart'):
            TCPServer.startService(self)
