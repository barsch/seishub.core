# -*- coding: utf-8 -*-
"""
A SFTP server.
"""

from seishub.config import IntOption, Option, BoolOption
from seishub.defaults import SFTP_AUTOSTART, SFTP_PORT, SFTP_PRIVATE_KEY, \
    SFTP_PUBLIC_KEY, SFTP_LOG_FILE
from seishub.exceptions import InternalServerError, ForbiddenError, \
    NotFoundError, SeisHubError
from seishub.processor import Processor, PUT, DELETE, GET, MOVE, HEAD, \
    getChildForRequest
from seishub.processor.interfaces import IFileSystemResource, IStatical, \
    IResource, IScriptResource, IRESTResource, IXMLIndex, IAdminResource
from seishub.util.ls import lsLine
from seishub.util.path import absPath
from twisted.application.internet import TCPServer #@UnresolvedImport
from twisted.conch import avatar, ssh
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch.interfaces import ISFTPFile, ISFTPServer, IConchUser
from twisted.conch.ssh.filetransfer import SFTPError, FX_FILE_ALREADY_EXISTS, \
    FX_FAILURE, FX_OP_UNSUPPORTED, FXF_READ, FXF_WRITE, FX_NO_SUCH_FILE
from twisted.cred import portal
from twisted.python import components
from zope.interface import implements
import StringIO
import os
import sys
#XXX:http://twistedmatrix.com/trac/ticket/3503
#from twisted.conch.ls import lsLine


__all__ = ['SFTPService']


DEFAULT_GID = 1000


class SFTPProcessor(Processor):
    """
    SFTP processor.
    """
    def render(self):
        """
        Renders the requested resource returned from the self.process() method.
        """
        # traverse the resource tree
        child = getChildForRequest(self.env.tree, self)
        # check result and either render direct or in thread
        if IFileSystemResource.providedBy(child):
            # render direct 
            return child.render(self)
        elif IStatical.providedBy(child):
            # render direct
            return child.render(self)
        elif IScriptResource.providedBy(child):
            msg = "Script resources may not be called via SFTP."
            raise ForbiddenError(msg)
        elif IRESTResource.providedBy(child):
            return child.render(self)
        elif IResource.providedBy(child):
            return child.render(self)
        msg = "I don't know how to handle this resource type %s"
        raise InternalServerError(msg % type(child))


class InMemoryFile:
    implements(ISFTPFile)

    def __init__(self, env, filename, flags, attrs={}):
        self.env = env
        self.env.log.debugx("InMemoryFile.init(%s, %s, %s)" % (repr(filename),
                                                               repr(flags),
                                                               repr(attrs)))
        self.filename = filename
        self.flags = flags
        self.attrs = attrs
        self.data = StringIO.StringIO('')
        if flags & FXF_READ:
            self._readFile(filename, flags, attrs)

    def _readFile(self, filename, flags, attrs):
        # read file via SFTP processor
        proc = SFTPProcessor(self.env)
        try:
            result = proc.run(GET, filename)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except:
            raise
        if IRESTResource.providedBy(result):
            # some REST resource
            try:
                data = result.render_GET(proc)
            except SeisHubError, e:
                raise SFTPError(FX_FAILURE, e.message)
            except:
                raise
            self.data = StringIO.StringIO(data)
        elif IFileSystemResource.providedBy(result):
            # some file system resource
            self.data = result.open()
        else:
            msg = "I don't know how to handle this resource type %s"
            raise SFTPError(FX_FAILURE, msg % type(result))

    def readChunk(self, offset, length):
        """
        Read from the file.
        
        If EOF is reached before any data is read, raise EOFError.
        
        This method returns the data as a string, or a Deferred that is
        called back with same.
        
        @param offset: an integer that is the index to start from in the file.
        @param length: the maximum length of data to return.  The actual amount
        returned may less than this.  For normal disk files, however,
        this should read the requested number (up to the end of the file).
        """
        self.env.log.debugx("InMemoryFile.readChunk(%s, %s)" % (repr(offset),
                                                                repr(length)))
        self.data.seek(offset)
        return self.data.read(length)

    def writeChunk(self, offset, data):
        """
        Write to the file.
        
        This method returns when the write completes, or a Deferred that is
        called when it completes.
        
        @param offset: an integer that is the index to start from in the file.
        @param data: a string that is the data to write.
        """
        self.env.log.debugx("InMemoryFile.writeChunk(%s, %d)" % (repr(offset),
                                                                 len(data)))
        self.data.seek(offset)
        self.data.write(data)

    def close(self):
        """
        Close the file.

        This method returns nothing if the close succeeds immediately, or a
        Deferred that is called back when the close succeeds.
        """
        self.env.log.debugx("InMemoryFile.close() - %s" % (self.filename))
        # create file
        self.data.seek(0)
        # write file after close
        if not self.data:
            return
        if not (self.flags & FXF_WRITE):
            return
        if not self.filename:
            return
        # check for resource
        proc = SFTPProcessor(self.env)
        try:
            # create new resource
            proc.run(PUT, self.filename, self.data)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except Exception, e:
            raise

    def getAttrs(self):
        """
        Return the attributes for the file.
        
        This method returns a dictionary in the same format as the attrs
        argument to L{openFile} or a L{Deferred} that is called back with same.
        """
        self.env.log.debugx("InMemoryFile.getAttrs()")
        return {}

    def setAttrs(self, attrs):
        """
        Set the attributes for the file.
        
        This method returns when the attributes are set or a Deferred that is
        called back when they are.
        
        @param attrs: a dictionary in the same format as the attrs argument to
        L{openFile}.
        """
        self.env.log.debugx("InMemoryFile.setAttrs(%s)" % (repr(attrs)))
        return


class SFTPServiceProtocol:
    implements(ISFTPServer)

    def __init__(self, avatar):
        self.avatar = avatar
        self.env = avatar.env

    def gotVersion(self, otherVersion, extData):
        """
        Called when the client sends their version info.
        
        otherVersion is an integer representing the version of the SFTP
        protocol they are claiming.
        extData is a dictionary of extended_name : extended_data items.
        These items are sent by the client to indicate additional features.
        
        This method should return a dictionary of extended_name : extended_data
        items.  These items are the additional features (if any) supported
        by the server.
        """
        return {}

    def webSafe(self, path):
        return path.decode(sys.getfilesystemencoding()).encode('utf-8')

    def realPath(self, path):
        """
        Convert any path to an absolute path.

        This method returns the absolute path as a string, or a Deferred
        that returns the same.

        @param path: the path to convert as a string.
        """
        self.env.log.debugx("realPath(%s)" % (repr(path)))
        path = self.webSafe(path)
        return absPath(path)

    def openFile(self, filename, flags, attrs):
        """
        Called when the clients asks to open a file.
        
        @param filename: a string representing the file to open.
        
        @param flags: an integer of the flags to open the file with, ORed together.
        The flags and their values are listed at the bottom of this file.
        
        @param attrs: a list of attributes to open the file with.  It is a
        dictionary, consisting of 0 or more keys.  The possible keys are::
        
            size: the size of the file in bytes
            uid: the user ID of the file as an integer
            gid: the group ID of the file as an integer
            permissions: the permissions of the file with as an integer.
            the bit representation of this field is defined by POSIX.
            atime: the access time of the file as seconds since the epoch.
            mtime: the modification time of the file as seconds since the epoch.
            ext_*: extended attributes.  The server is not required to
            understand this, but it may.
        
        NOTE: there is no way to indicate text or binary files.  it is up
        to the SFTP client to deal with this.
        
        This method returns an object that meets the ISFTPFile interface.
        Alternatively, it can return a L{Deferred} that will be called back
        with the object.
        """
        self.env.log.debugx("openFile(%s, %s, %s)" % (repr(filename),
                                                      repr(flags),
                                                      repr(attrs)))
        # lockup filename in utf-8
        filename = self.webSafe(filename)
        if flags & FXF_READ == FXF_READ:
            return InMemoryFile(self.env, filename, flags, attrs)
        elif flags & FXF_WRITE == FXF_WRITE:
            return self._writeFile(filename, flags, attrs)
        else:
            msg = "Don't know how to handle this request"
            raise SFTPError(FX_FAILURE, msg)

    def _writeFile(self, filename, flags, attrs):
        # check if file exists
        proc = SFTPProcessor(self.env)
        try:
            proc.run(HEAD, filename)
        except NotFoundError:
            return InMemoryFile(self.env, filename, flags, attrs)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except:
            raise
        raise SFTPError(FX_FILE_ALREADY_EXISTS, "File already exists.")

    def openDirectory(self, path):
        """
        Open a directory for scanning.
        
        This method returns an iterable object that has a close() method,
        or a Deferred that is called back with same.
        
        The close() method is called when the client is finished reading
        from the directory.  At this point, the iterable will no longer
        be used.
        
        The iterable should return triples of the form (filename,
        longname, attrs) or Deferreds that return the same.  The
        sequence must support __getitem__, but otherwise may be any
        'sequence-like' object.
        
        filename is the name of the file relative to the directory.
        logname is an expanded format of the filename.  The recommended format
        is:
        -rwxr-xr-x   1 mjos     staff      348911 Mar 25 14:29 t-filexfer
        1234567890 123 12345678 12345678 12345678 123456789012
        
        The first line is sample output, the second is the length of the field.
        The fields are: permissions, link count, user owner, group owner,
        size in bytes, modification time.
        
        attrs is a dictionary in the format of the attrs argument to openFile.
        
        @param path: the directory to open.
        """
        self.env.log.debugx("openDirectory(%s)" % (repr(path)))
        # lockup filename in utf-8
        path = self.webSafe(path)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        try:
            result = proc.run(HEAD, path)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except:
            raise
        # check if we got a folder
        if not isinstance(result, dict):
            msg = 'Expected a dictionary or basestring.'
            raise InternalServerError(msg)
        # build up a file list
        filelist = []
        filelist.append(('.', {}))
        filelist.append(('..', {}))
        # cycle through all objects and add only known resources
        ids = sorted(result)
        for id in ids:
            obj = result.get(id)
            # skip hidden objects
            if obj.hidden:
                continue
            if IXMLIndex.providedBy(obj):
                continue
            if IAdminResource.providedBy(obj):
                continue
            attrs = obj.getMetadata()
            if attrs:
                # return ids in system encoding
                fsid = id.decode('utf-8').encode(sys.getfilesystemencoding())
                filelist.append((fsid, attrs))
        return DirList(self.env, iter(filelist))

    def getAttrs(self, path, followLinks):
        """
        Return the attributes for the given path.
        
        This method returns a dictionary in the same format as the attrs
        argument to openFile or a Deferred that is called back with same.
        
        @param path: the path to return attributes for as a string.
        @param followLinks: a boolean.  If it is True, follow symbolic links
        and return attributes for the real path at the base.  If it is False,
        return attributes for the specified path.
        """
        self.env.log.debugx("openDirectory(%s, %s)" % (repr(path),
                                                       repr(followLinks)))
        # lockup filename in utf-8
        path = self.webSafe(path)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        try:
            result = proc.run(GET, path)
        except NotFoundError:
            raise SFTPError(FX_NO_SUCH_FILE, '')
        except:
            raise
        else:
            if isinstance(result, dict):
                return {'permissions': 040755}
            else:
                return result.getMetadata()

    def setAttrs(self, path, attrs):
        """
        Set the attributes for the path.
        
        This method returns when the attributes are set or a Deferred that is
        called back when they are.
        
        @param path: the path to set attributes for as a string.
        @param attrs: a dictionary in the same format as the attrs argument to
        L{openFile}.
        """
        self.env.log.debugx("setAttrs(%s, %s)" % (repr(path), repr(attrs)))
        return

    def removeFile(self, filename):
        """
        Remove the given file.
        
        This method returns when the remove succeeds, or a Deferred that is
        called back when it succeeds.
        
        @param filename: the name of the file as a string.
        """
        self.env.log.debugx("removeFile(%s)" % (filename))
        # lockup filename in utf-8
        filename = self.webSafe(filename)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        try:
            proc.run(DELETE, filename)
        except ForbiddenError, e:
            raise SFTPError(FX_OP_UNSUPPORTED, e.message)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except:
            raise

    def renameFile(self, oldpath, newpath):
        """
        Rename the given file.
        
        This method returns when the rename succeeds, or a L{Deferred} that is
        called back when it succeeds. If the rename fails, C{renameFile} will
        raise an implementation-dependent exception.
        
        @param oldpath: the current location of the file.
        @param newpath: the new file name.
        """
        self.env.log.debugx("renameFile(%s, %s)" % (oldpath, newpath))
        # lockup filename in utf-8
        oldpath = self.webSafe(oldpath)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        destination = self.env.getRestUrl() + newpath
        try:
            proc.run(MOVE, oldpath,
                     received_headers={'Destination': destination})
        except ForbiddenError, e:
            raise SFTPError(FX_OP_UNSUPPORTED, e.message)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except:
            raise

    def makeDirectory(self, path, attrs):
        """
        Make a directory.
        
        This method returns when the directory is created, or a Deferred that
        is called back when it is created.
        
        @param path: the name of the directory to create as a string.
        @param attrs: a dictionary of attributes to create the directory with.
        Its meaning is the same as the attrs in the L{openFile} method.
        """
        msg = "Directories can't be added via SFTP."
        raise SFTPError(FX_OP_UNSUPPORTED, msg)

    def removeDirectory(self, path):
        """
        Remove a directory (non-recursively)
        
        It is an error to remove a directory that has files or directories in
        it.
        
        This method returns when the directory is removed, or a Deferred that
        is called back when it is removed.
        
        @param path: the directory to remove.
        """
        msg = "Directories can't be deleted via SFTP."
        raise SFTPError(FX_OP_UNSUPPORTED, msg)

    def readLink(self, path):
        msg = "Symbolic links are not supported yet."
        raise SFTPError(FX_OP_UNSUPPORTED, msg)

    def makeLink(self, linkPath, targetPath):
        msg = "Symbolic can'T be created via SFTP."
        raise SFTPError(FX_OP_UNSUPPORTED, msg)


class DirList:
    def __init__(self, env, iter):
        self.env = env
        self.env.log.debugx("DirList.__init__(%s)" % (repr(iter)))
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
        attrs['gid'] = s.st_gid = attrs.get('gid', DEFAULT_GID)
        attrs['size'] = s.st_size = attrs.get('size', 0)
        attrs['atime'] = s.st_atime = int(attrs.get('atime',
                                                    self.env.startup_time))
        attrs['mtime'] = s.st_mtime = int(attrs.get('mtime',
                                                    self.env.startup_time))
        attrs['nlink'] = s.st_nlink = 1
        return (name, lsLine(name, s), attrs)

    def close(self):
        return


class SFTPServiceAvatar(avatar.ConchUser):

    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({"session": ssh.session.SSHSession})
        self.subsystemLookup.update({"sftp":
                                     ssh.filetransfer.FileTransferServer})

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


class SFTPServiceFactory(SSHFactory):
    """
    Factory for SFTP server.
    """
    def __init__(self, env):
        self.env = env
        self.portal = portal.Portal(SFTPServiceRealm(env),
                                    env.auth.getCheckers())
        #set keys
        pub, priv = self._getCertificates()
        self.publicKeys = {'ssh-rsa': ssh.keys.Key.fromFile(pub)}
        self.privateKeys = {'ssh-rsa': ssh.keys.Key.fromFile(priv)}
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
        pub_key = ssh.keys.Key(rsa_key).public().toString('openssh')
        file(pub_file, 'w+b').write(str(pub_key))
        msg = "Private key file %s has been created."
        self.env.log.warn(msg % pub_file)
        # private key
        priv_key = ssh.keys.Key(rsa_key).toString('openssh')
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
    service_id = "sftp"

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
