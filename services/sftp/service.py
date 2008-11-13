# -*- coding: utf-8 -*-

import os
import time
import StringIO

from zope.interface import implements

from twisted.application import internet
from twisted.conch.ssh import factory, keys, common, session, filetransfer
from twisted.conch.interfaces import ISFTPFile, ISFTPServer, IConchUser
from twisted.conch import avatar
from twisted.cred import portal
from twisted.python import components

from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY
from seishub.defaults import SFTP_AUTOSTART
from seishub.config import IntOption, Option, BoolOption
from seishub.packages.processor import Processor
from seishub.exceptions import SeisHubError
from seishub.packages.processor import PUT, POST, DELETE, GET, MOVE
from seishub.util.path import absPath, lsLine


DEFAULT_GID = 1000


class DirList:
    def __init__(self, env, iter):
        self.iter = iter
        self.env = env
    
    def __iter__(self):
        return self
    
    def next(self):
        (name, attrs) = self.iter.next()
        
        class st:
            pass
        
        s = st()
        attrs['permissions'] = s.st_mode = attrs.get('permissions', 040755)
        attrs['uid'] = s.st_uid = attrs.get('uid', 0)
        attrs['gid'] = s.st_gid = attrs.get('gid', DEFAULT_GID)
        attrs['size'] = s.st_size = attrs.get('size', 0)
        attrs['atime'] = s.st_atime = attrs.get('atime', self.env.startup_time)
        attrs['mtime'] = s.st_mtime = attrs.get('mtime', self.env.startup_time)
        attrs['nlink'] = s.st_nlink = 1
        return ( name, lsLine(name, s), attrs )
    
    def close(self):
        return


class InMemoryFile:
    implements(ISFTPFile)
    
    def __init__(self, env, filename, flags, attrs):
        self.env = env
        self.filename = filename
        self.flags = flags
        self.attrs = attrs
        self.data = StringIO.StringIO()
        self.proc = Processor(self.env)
        if self.flags & filetransfer.FXF_READ:
            result = self._readResource()
            if result:
                self.data.write(result)
            else:
                raise filetransfer.SFTPError(filetransfer.FX_NO_SUCH_FILE, '')
    
    def _readResource(self):
        # check if resource exists
        data = ''
        try:
            data = self.proc.run(GET, self.filename)
        except:
            pass
        return data
    
    def readChunk(self, offset, length):
        self.data.seek(offset)
        return self.data.read(length)
    
    def writeChunk(self, offset, data):
        self.data.seek(offset)
        self.data.write(data)
    
    def close(self):
        # write file after close 
        if not self.data:
            return
        if not (self.flags & filetransfer.FXF_WRITE):
            return
        # check for resource
        result = self._readResource()
        self.proc.content = self.data
        self.proc.path = self.filename
        if result:
            # resource exists
            self.proc.method = POST
        else:
            # new resource
            self.proc.method = PUT
        try:
            self.proc.process()
        except SeisHubError, e:
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, e.message)
    
    def getAttrs(self):
        pass
    
    def setAttrs(self, attrs):
        pass


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
        return InMemoryFile(self.env, filename, flags, attrs)
    
    def openDirectory(self, path):
        # remove trailing slashes
        path = absPath(path)
        proc = Processor(self.env)
        try:
            data = proc.run(GET, path)
        except Exception, e:
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, e.message)
        filelist = []
        filelist.append(('.', {}))
        filelist.append(('..', {}))
        
        # packages, resourcetypes, aliases and mappings are directories
        for t in ['package', 'resourcetype', 'alias', 'mapping', 'folder']:
            for d in data.get(t,[]):
                name = d.split('/')[-1]
                filelist.append((name, {}))
        # properties are XML documents
        # XXX: missing yet
        
        # fetch all resources
        resources = data.get('resource',[])
        for obj in resources:
            if isinstance(obj, basestring):
                # XXX: workaround for mappers, should be removed 
                file_name = obj.split('/')[-1:][0]
                filelist.append((file_name, {'permissions': 0100644}))
            else:
                # resource object
                file_name = str(obj).split('/')[-1:][0]
                temp = obj.document.meta.datetime
                file_datetime = int(time.mktime(temp.timetuple()))
                file_size = obj.document.meta.size
                file_uid = obj.document.meta.uid or 0
                filelist.append((file_name, {'permissions': 0100644,
                                             'uid': file_uid,
                                             'size': file_size,
                                             'atime': file_datetime,
                                             'mtime': file_datetime}))
        return DirList(self.env, iter(filelist))
    
    def getAttrs(self, filename, followLinks):
        # remove trailing slashes
        filename = absPath(filename)
        # process resource
        proc = Processor(self.env)
        data = None
        try:
            data = proc.run(GET, filename)
        except SeisHubError, e:
            pass
        except Exception, e:
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, e.message)
        if isinstance(data, basestring):
            # file
            perm = 0100644
        else:
            # directory
            perm = 040755
        return {'permissions': perm, 
                'size': 0, 
                'uid': 0, 
                'gid': DEFAULT_GID, 
                'atime': self.env.startup_time, 
                'mtime': self.env.startup_time, 
                'nlink': 1} 
    
    def setAttrs(self, path, attrs):
        return
    
    def removeFile(self, filename):
        """Remove the given file.
        
        @param filename: the name of the file as a string.
        """
        # process resource
        proc = Processor(self.env)
        try:
            proc.run(DELETE, filename)
        except Exception, e:
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, e.message)
    
    def renameFile(self, oldpath, newpath):
        # process resource
        proc = Processor(self.env)
        destination = self.env.getRestUrl() + newpath
        try:
            proc.run(MOVE, oldpath, 
                     received_headers={'Destination': destination})
        except Exception, e:
            raise filetransfer.SFTPError(filetransfer.FX_FAILURE, e.message)
        return
    
    def makeDirectory(self, path, attrs):
        msg = "Directories can't be added via SFTP."
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, msg)
    
    def removeDirectory(self, path):
        msg = "Directories can't be deleted via SFTP."
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED,msg)
    
    def readLink(self, path):
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')
    
    def makeLink(self, linkPath, targetPath):
        raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, '')


class SFTPServiceAvatar(avatar.ConchUser):
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.listeners = {}
        self.channelLookup.update({"session": session.SSHSession})
        self.subsystemLookup.update({"sftp": filetransfer.FileTransferServer})
    
    def logout(self):
        self.env.log.info('User %s logging out (%i)' % (self.username, 
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
        self.portal = portal.Portal(SFTPServiceRealm(env), 
                                    env.auth.getCheckers())
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
    
    BoolOption('sftp', 'autostart', SFTP_AUTOSTART, 
               'Enable service on start-up.')
    IntOption('sftp', 'port', SFTP_PORT, "SFTP port number.")
    Option('sftp', 'public_key_file', SFTP_PUBLIC_KEY, 'Public RSA key file.')
    Option('sftp', 'private_key_file', SFTP_PRIVATE_KEY, 
           'Private RSA key file.')
    
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
