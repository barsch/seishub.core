# -*- coding: utf-8 -*-

import os
import time

from zope.interface import implements
from twisted.python import components
from twisted.cred import portal
from twisted.conch.ssh import factory, keys, common, session, filetransfer
from twisted.conch import avatar, interfaces as conchinterfaces
from twisted.application import internet
from twisted.conch.ls import lsLine

#from seishub import __version__ as SEISHUB_VERSION
from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY
from seishub.config import IntOption, Option
from seishub.packages.processor import Processor, RequestError
from seishub.util.path import absPath


class SFTPServiceProtocol:
    implements(filetransfer.ISFTPServer)
    
    def __init__(self, avatar):
        self.avatar = avatar
        self.env = avatar.env
    
    def gotVersion(self, otherVersion, extData):
        print "gotVersion"
        print otherVersion
        print extData
        return {}
    
    def realPath(self, path):
        return absPath(path)
    
    def openFile(self, filename, flags, attrs):
        print "openFile"
        print filename
        print flags
        print attrs
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')

    def removeFile(self, filename):
        print "removeFile"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def openDirectory(self, path):
        request = Processor(self.env)
        request.method = 'GET'
        request.path = path
        try:
            data = request.process()
        except RequestError, e:
            self.env.log.error('RequestError:', str(e))
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, str(e))
        
        filelist = []
        attr = {'permissions': 16877, 'size': 0, 'uid': 0, 'gid': 0,
                'atime': time.time(), 'mtime': time.time(), 'nlink': 1}
        filelist.append(('.', attr))
        filelist.append(('..', attr))
        # packages, resource types, aliases and mappings are directories
        for r in ['package','resourcetype','alias','mapping']:
            for d in data.get(r,[]):
                filelist.append((d, self._attrify(d, False)))
        # direct resources will be documents
        for d in data.get('resource',[]):
            filelist.append((str(d), self._attrify(d, True)))
        
        class DirList:
            def __init__(self, iter):
                self.iter = iter
            def __iter__(self):
                return self
            
            def next(self):
                (name, attrs) = self.iter.next()
                
                class st:
                    pass
                
                s = st()
                s.st_mode   = attrs["permissions"]
                s.st_uid    = attrs["uid"]
                s.st_gid    = attrs["gid"]
                s.st_size   = attrs["size"]
                s.st_mtime  = attrs["mtime"]
                s.st_nlink  = attrs["nlink"]
                return ( name, lsLine(name, s), attrs )
            
            def close(self):
                return
        
        return DirList(iter(filelist))
    
    def getAttrs(self, path, followLinks):
        return self._attrify(path)
    
    def setAttrs(self, path, attrs):
        print "setAttrs"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def makeDirectory(self, path, attrs):
        print "makeDirectory"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def removeDirectory(self, path):
        print "removeDirectory"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def readLink(self, path):
        print "readLink"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def makeLink(self, linkPath, targetPath):
        print "makeLink"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def renameFile(self, oldpath, newpath):
        print "renameFile"
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def _attrify(self, path, file=False):
        if file:
            attr = {'permissions': 33188, 'size': 10000, 'uid': 0, 'gid': 0,
                    'atime': time.time(), 'mtime': time.time(), 'nlink': 0}
        else:
            attr = {'permissions': 16877, 'size': 0, 'uid': 0, 'gid': 0,
                    'atime': time.time(), 'mtime': time.time(), 'nlink': 1}
        return attr


class SFTPServiceAvatar(avatar.ConchUser):
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.listeners = {}
        self.channelLookup.update({"session": session.SSHSession})
        self.subsystemLookup.update({"sftp": filetransfer.FileTransferServer})
    
    def logout(self):
        self.env.log.info('avatar %s logging out (%i)' % (self.username, 
                                                          len(self.listeners)))

components.registerAdapter(SFTPServiceProtocol, SFTPServiceAvatar, 
                           filetransfer.ISFTPServer)


#class SFTPServiceSession:
#    implements(session.ISession)
#    
#    def __init__(self, avatar):
#        self.avatar = avatar
#    
#    def openShell(self, proto):
#            self.avatar.conn.transport.transport.loseConnection()
#    
#    def getPty(self, term, windowSize, modes):
#        pass
#    
#    def closed(self):
#        pass
#
#components.registerAdapter(SFTPServiceSession, SFTPServiceAvatar, 
#                           session.ISession)


class SFTPServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if conchinterfaces.IConchUser in interfaces:
            return interfaces[0], SFTPServiceAvatar(avatarId, self.env), \
                   lambda: None
        else:
            raise Exception, "No supported interfaces found."


class SFTPServiceFactory(factory.SSHFactory):
    """Factory for SFTP Server."""
    
    def __init__(self, env):
        self.env = env
        self.portal = portal.Portal(SFTPServiceRealm(env), env.auth)
        #set keys
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
