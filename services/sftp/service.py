# -*- coding: utf-8 -*-

import os
import time

from cStringIO import StringIO
from zope.interface import implements

from twisted.application import internet
from twisted.conch.ssh import factory, keys, common, session
from twisted.conch.ssh.filetransfer import FileTransferServer, SFTPError, \
                                           FX_OP_UNSUPPORTED, FX_FAILURE
from twisted.conch.interfaces import ISFTPFile, ISFTPServer, IConchUser
from twisted.conch import avatar
from twisted.conch.ls import lsLine
from twisted.cred import portal
from twisted.python import components

#from seishub import __version__ as SEISHUB_VERSION
from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY
from seishub.config import IntOption, Option, BoolOption
from seishub.packages.processor import Processor, RequestError
from seishub.util.path import absPath


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
        attrs['permissions'] = s.st_mode = attrs.get('permissions', 040755)
        attrs['uid'] = s.st_uid = attrs.get('uid', 0)
        attrs['gid'] = s.st_gid = attrs.get('gid', 0)
        attrs['size'] = s.st_size = attrs.get('size', 0)
        attrs['atime'] = s.st_atime = attrs.get('atime', time.time())
        attrs['mtime'] = s.st_mtime = attrs.get('mtime', time.time())
        attrs['nlink'] = s.st_nlink = 1
        return ( name, lsLine(name, s), attrs )
    
    def close(self):
        return


class InMemoryFile:
    implements(ISFTPFile)
    
    def __init__(self, data=''):
        self.data = StringIO()
        self.data.write(data)
    
    def readChunk(self, offset, length):
        self.data.seek(offset)
        return self.data.read(length)
    
    def writeChunk(self, offset, data):
        self.data.seek(offset)
        self.data.write(data)
    
    def close(self):
        pass
    
    def getAttrs(self):
        print "-------------file.getAttrs"
        return {'permissions': 020755, 'size': 0, 'uid': 0, 'gid': 0,
                'atime': time.time(), 'mtime': time.time()}
    
    def setAttrs(self, attrs):
        print "-------------file.setAttrs"
        raise SFTPError(FX_OP_UNSUPPORTED, '')


class SFTPServiceProtocol:
    implements(ISFTPServer)
    
    def __init__(self, avatar):
        self.avatar = avatar
        self.env = avatar.env
    
    def gotVersion(self, otherVersion, extData):
        return {}
    
    def realPath(self, path):
        return absPath(path)
    
    def openFile(self, filename, flags, attrs):
        print "-------------openFile", filename, flags, attrs
        # fetch the symbolic link path
        path = self.readLink(filename[:-4])
        # process resource
        request = Processor(self.env)
        request.method = 'GET'
        request.path = path
        try:
            data = request.process()
        except RequestError, e:
            self.env.log.error('RequestError:', str(e))
            raise SFTPError(FX_FAILURE, str(e))
        return InMemoryFile(data)
    
    def openDirectory(self, path):
        print "-------------openDirectory", path
        request = Processor(self.env)
        request.method = 'GET'
        request.path = path
        try:
            data = request.process()
        except RequestError, e:
            self.env.log.error('RequestError:', str(e))
            raise SFTPError(FX_FAILURE, str(e))
        filelist = []
        filelist.append(('.', {}))
        filelist.append(('..', {}))
        # packages are readable directories
        for d in data.get('package',[]):
            name = d[1:]
            filelist.append((name, {}))
        # resourcetypes are readable directories
        for d in data.get('resourcetype',[]):
            name = d[1+len(path):]
            filelist.append((name, {}))
        # alias are readable directories
        for d in data.get('alias',[]):
            name = d[1+len(path):]
            filelist.append((name, {}))
        # mappers are readable directories
        for d in data.get('mapping',[]):
            name = d[1+len(path):]
            filelist.append((name, {}))
        # .all directory
        if path+'/'+'.all' in data.get('property',[]):
            filelist.append(('.all', {}))
        # direct resource will be a symbolic link to a document
        for d in data.get('resource',[]):
            name = d.split('/')[-1:][0]
            print name
            filelist.append((name+'.xml', {'permissions': 0120777, 
                                           'size': len(d)}))
        return DirList(iter(filelist))
    
    def getAttrs(self, path, followLinks):
        print "-------------getAttrs", path, followLinks
        return {'permissions': 020755, 'size': 0, 'uid': 0, 'gid': 0,
                'atime': time.time(), 'mtime': time.time()}
    
    def readLink(self, path):
        """Find the root of a set of symbolic links."""
        print "-------------readLink", path
        temp = path.split('/')
        name = '/' + temp[1] + '/' + temp[2] + '/' + temp[-1:][0]
        return name
    
    def setAttrs(self, path, attrs):
        raise SFTPError(FX_OP_UNSUPPORTED, '')
    
    def removeFile(self, filename):
        raise SFTPError(FX_OP_UNSUPPORTED, '')
    
    def renameFile(self, oldpath, newpath):
        raise SFTPError(FX_OP_UNSUPPORTED, '')
    
    def makeDirectory(self, path, attrs):
        raise SFTPError(FX_OP_UNSUPPORTED, '')
    
    def removeDirectory(self, path):
        raise SFTPError(FX_OP_UNSUPPORTED, '')
    
    def makeLink(self, linkPath, targetPath):
        raise SFTPError(FX_OP_UNSUPPORTED, '')


class SFTPServiceAvatar(avatar.ConchUser):
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.listeners = {}
        self.channelLookup.update({"session": session.SSHSession})
        self.subsystemLookup.update({"sftp": FileTransferServer})
    
    def logout(self):
        self.env.log.info('avatar %s logging out (%i)' % (self.username, 
                                                          len(self.listeners)))

components.registerAdapter(SFTPServiceProtocol, SFTPServiceAvatar, ISFTPServer)


class SFTPServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IConchUser in interfaces:
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


class SFTPService(internet.TCPServer): #@UndefinedVariable
    """Service for SFTP server."""
    BoolOption('sftp', 'autostart', 'True', "Enable service on start-up.")
    IntOption('sftp', 'port', SFTP_PORT, "SFTP port number.")
    Option('sftp', 'public_key_file', SFTP_PUBLIC_KEY, 'Public RSA key file.')
    Option('sftp', 'private_key_file', SFTP_PRIVATE_KEY, 'Private RSA key file.')
    
    def __init__(self, env):
        self.env = env
        port = env.config.getint('sftp', 'port')
        internet.TCPServer.__init__(self, #@UndefinedVariable
                                    port, SFTPServiceFactory(env))
        self.setName("SFTP")
        self.setServiceParent(env.app)
    
    def privilegedStartService(self):
        if self.env.config.getbool('sftp', 'autostart'):
            internet.TCPServer.privilegedStartService(self) #@UndefinedVariable
    
    def startService(self):
        if self.env.config.getbool('sftp', 'autostart'):
            internet.TCPServer.startService(self) #@UndefinedVariable
