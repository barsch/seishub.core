# -*- coding: utf-8 -*-

import os
import time
import StringIO

from zope.interface import implements

from twisted.application import internet
from twisted.conch.ssh import factory, keys, common, session
from twisted.conch.ssh.filetransfer import FileTransferServer, SFTPError
from twisted.conch.interfaces import ISFTPFile, ISFTPServer, IConchUser
from twisted.conch import avatar
from twisted.conch.ls import lsLine
from twisted.cred import portal
from twisted.python import components

#from seishub import __version__ as SEISHUB_VERSION
from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY, \
                             SFTP_AUTOSTART
from seishub.config import IntOption, Option, BoolOption
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET
from seishub.util.path import absPath


FXF_READ          = 0x00000001
FXF_WRITE         = 0x00000002
FXF_APPEND        = 0x00000004
FXF_CREAT         = 0x00000008
FXF_TRUNC         = 0x00000010
FXF_EXCL          = 0x00000020
FXF_TEXT          = 0x00000040

FX_OK                          = 0
FX_EOF                         = 1
FX_NO_SUCH_FILE                = 2
FX_PERMISSION_DENIED           = 3
FX_FAILURE                     = 4
FX_BAD_MESSAGE                 = 5
FX_NO_CONNECTION               = 6
FX_CONNECTION_LOST             = 7
FX_OP_UNSUPPORTED              = 8
FX_FILE_ALREADY_EXISTS         = FX_FAILURE
FX_NOT_A_DIRECTORY             = FX_FAILURE
FX_FILE_IS_A_DIRECTORY         = FX_FAILURE


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
    
    def __init__(self, env, filename, flags, attrs):
        print "-------------file.__init__", filename, flags, attrs
        self.env = env
        self.filename = filename
        self.flags = flags
        self.attrs = attrs
        self.data = StringIO.StringIO()
        self.proc = Processor(self.env)
        if self.flags & FXF_READ:
            result = self._readResource()
            if result:
                self.data.write(result)
            else:
                raise SFTPError(FX_NO_SUCH_FILE)
    
    def _readResource(self):
        print "-------------file._readResource"
        # check if resource exists
        data = ''
        try:
            data = self.proc.run(GET, self.filename)
        except Exception:
            pass
        return data
    
    def readChunk(self, offset, length):
        print "-------------file.read", offset, length
        self.data.seek(offset)
        return self.data.read(length)
    
    def writeChunk(self, offset, data):
        print "-------------file.write", offset
        self.data.seek(offset)
        self.data.write(data)
    
    def close(self):
        print "-------------file.close"
        # write file after close 
        if not self.data:
            return
        if not (self.flags & FXF_WRITE):
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
        except ProcessorError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except Exception, e:
            raise SFTPError(FX_FAILURE, e)
    
    def getAttrs(self):
        print "-------------file.getAttrs"
        pass
    
    def setAttrs(self, attrs):
        print "-------------file.setAttrs", attrs
        pass


class SFTPServiceProtocol:
    implements(ISFTPServer)
    
    def __init__(self, avatar):
        self.avatar = avatar
        self.env = avatar.env
    
    def _removeFileExtension(self, filename):
        if '.' in filename:
            parts = filename.split('.')
            if parts[-1] in ['xml', 'xsd', 'xslt']:
                filename = '.'.join(parts[0:-1])
        return filename
    
    def gotVersion(self, otherVersion, extData):
        return {}
    
    def realPath(self, path):
        return absPath(path)
    
    def openFile(self, filename, flags, attrs):
        print "-------------openFile", filename, flags, attrs
        # remove file extension 
        filename = self._removeFileExtension(filename)
        return InMemoryFile(self.env, filename, flags, attrs)
    
    def openDirectory(self, path):
        print "-------------openDirectory", path
        # remove trailing slahes
        path = absPath(path)
        proc = Processor(self.env)
        try:
            data = proc.run(GET, path)
        except Exception, e:
            raise SFTPError(FX_FAILURE, e)
        filelist = []
        filelist.append(('.', {}))
        filelist.append(('..', {}))
        
        # packages, resourcetypes, aliases and mappings are directories
        for t in ['package', 'resourcetype', 'alias', 'mapping']:
            for d in data.get(t,[]):
                name = d.split('/')[-1]
                filelist.append((name, {}))
        # properties are XML documents
        # XXX: missing yet
        
        # stop here if no resources are given
        resources = data.get('resource',[])
        if not resources:
            return DirList(iter(filelist))
        # set default file extensions and permissions
        if path == '/seishub/schema':
            ext = '.xsd'
            perm = 0100644
        elif path == '/seishub/stylesheet':
            ext = '.xslt'
            perm = 0100644
        else:
            ext = '.xml'
            perm = 0100644
        # fetch all resources
        for d in resources:
            name = d.split('/')[-1:][0]
            # XXX: len should be indexed!! -> metadata ?
            filelist.append((name + ext, {'permissions': perm,
                                          'size': len(d)}))
        return DirList(iter(filelist))
    
    def getAttrs(self, filename, followLinks):
        print "-------------getAttrs", filename, followLinks
        # remove file extension 
        filename = self._removeFileExtension(filename)
        # remove trailing slashes
        filename = absPath(filename)
        # process resource
        proc = Processor(self.env)
        try:
            data = proc.run(GET, filename)
        except ProcessorError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except Exception, e:
            raise SFTPError(FX_FAILURE, e)
        if isinstance(data, basestring):
            # file
            # XXX: metadata here!!
            return {'permissions': 0100644, 'size': 0, 'uid': 0, 'gid': 0,
                    'atime': time.time(), 'mtime': time.time(), 'nlink': 1}
        else:
            # directory
            return {'permissions': 040755, 'size': 0, 'uid': 0, 'gid': 0,
                    'atime': time.time(), 'mtime': time.time(), 'nlink': 1}
    
    def setAttrs(self, path, attrs):
        print "-------------setAttrs", path, attrs
        return
    
    def removeFile(self, filename):
        """
        Remove the given file.
        
        @param filename: the name of the file as a string.
        """
        print "-------------removeFile", filename
        # remove file extension 
        filename = self._removeFileExtension(filename)
        # process resource
        proc = Processor(self.env)
        try:
            proc.run(DELETE, filename)
        except ProcessorError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except Exception, e:
            raise SFTPError(FX_FAILURE, e)
    
    def renameFile(self, oldpath, newpath):
        print "-------------renameFile", oldpath, newpath
        return
    
    def makeDirectory(self, path, attrs):
        raise SFTPError(FX_OP_UNSUPPORTED, 
                        "Directories can't be added via SFTP.")
    
    def removeDirectory(self, path):
        raise SFTPError(FX_OP_UNSUPPORTED, 
                        "Directories can't be deleted via SFTP.")
    
    def readLink(self, path):
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
