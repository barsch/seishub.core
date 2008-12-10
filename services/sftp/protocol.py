# -*- coding: utf-8 -*-

from seishub.exceptions import NotAllowedError, InternalServerError, \
    ForbiddenError
from seishub.processor import Processor, PUT, DELETE, GET, MOVE, HEAD, \
    getChildForRequest
from seishub.processor.interfaces import IFileSystemResource, IStaticResource, \
    IResource, IScriptResource
from seishub.util.path import absPath, lsLine
from twisted.conch.interfaces import ISFTPFile, ISFTPServer
from twisted.conch.ssh.filetransfer import SFTPError, FX_FAILURE, \
    FX_OP_UNSUPPORTED, FXF_READ, FXF_CREAT
from twisted.internet import defer, threads
from twisted.python.failure import Failure
from zope.interface import implements
import StringIO
import sys


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
        result = getChildForRequest(self.env.tree, self)
        # check result and either render direct or in thread
        if IFileSystemResource.providedBy(result):
            # render direct 
            return result.render(self)
        elif IStaticResource.providedBy(result):
            # render direct
            return result.render(self)
        elif IScriptResource.providedBy(result):
            msg = "Script resources may not be called via SFTP."
            raise ForbiddenError(msg)
        elif IResource.providedBy(result):
            # render in thread
            return threads.deferToThread(result.render, self)
        msg = "I don't know how to handle this resource type %s"
        raise InternalServerError(msg % type(result))


class InMemoryFile:
    implements(ISFTPFile)
    
    def __init__(self, data):
        self.data = data
    
    def readChunk(self, offset, length):
        self.data.seek(offset)
        return self.data.read(length)
    
    def writeChunk(self, offset, data):
        self.data.seek(offset)
        self.data.write(data)
    
    def close(self):
        pass
    
    def getAttrs(self):
        pass
    
    def setAttrs(self, attrs):
        pass


class SFTPServiceProtocol:
    implements(ISFTPServer)
    
    def __init__(self, avatar):
        self.avatar = avatar
        self.env = avatar.env
        self.create_files = {}
    
    def gotVersion(self, otherVersion, extData):
        return {}
    
    def webSafe(self, path):
        return path.decode(sys.getfilesystemencoding()).encode('utf-8')
    
    def realPath(self, path):
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
        # lockup filename in utf-8
        filename = self.webSafe(filename)
        # query the directory via SFTP processor
        if flags & FXF_READ == FXF_READ:
            # read file
            proc = SFTPProcessor(self.env)
            d = defer.maybeDeferred(proc.run, GET, filename)
            d.addCallback(self._cbRenderFile)
            d.addErrback(self._cbFailed)
            return d
        elif flags & FXF_CREAT == FXF_CREAT:
            # create file
            data = StringIO.StringIO('')
            imf = InMemoryFile(data)
            self.create_files[filename] = (imf, flags)
            return imf
        msg = "Don't know how to handle this request"
        raise SFTPError(FX_FAILURE, msg)
    
    def _cbRenderFile(self, result):
        if isinstance(result, basestring):
            # some basestring object
            data = StringIO.StringIO(result)
            return InMemoryFile(data)
        elif IFileSystemResource.providedBy(result):
            # some file system resource
            data = result.open()
            return InMemoryFile(data)
        msg = "I don't know how to handle this resource type %s"
        raise InternalServerError(msg % type(result))
    
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
        # lockup filename in utf-8
        path = self.webSafe(path)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        d = defer.maybeDeferred(proc.run, HEAD, path)
        d.addCallback(self._cbRenderFolder)
        d.addErrback(self._cbFailed)
        return d
    
    def _cbFailed(self, failure):
        if not isinstance(failure, Failure):
            raise
        if isinstance(failure.value, SFTPError):
            # this is a SFTP error
            raise failure.value
        elif 'seishub.exceptions.SeisHubError' in failure.parents:
            # this is a SeisHubError
            self.env.log.http(failure.value.code, failure.value.message)
            if isinstance(failure, NotAllowedError):
                err = FX_OP_UNSUPPORTED
            else:
                err = FX_FAILURE
            raise SFTPError(err, failure.value.message)
        else:
            # we got something unhandled yet
            self.env.log.error(failure.getTraceback())
            raise SFTPError(FX_FAILURE, failure.getErrorMessage())
    
    def _cbRenderFolder(self, obj_dict):
        # check if we got a folder
        if not isinstance(obj_dict, dict):
            msg = 'Expected a dictionary or basestring.'
            raise InternalServerError(msg)
        # build up a file list
        filelist = []
        filelist.append(('.', {}))
        filelist.append(('..', {}))
        # cycle through all objects and add only known resources
        ids = sorted(obj_dict)
        for id in ids:
            obj = obj_dict.get(id)
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
        
        @param path:        the path to return attributes for as a string.
        @param followLinks: a boolean.  If it is True, follow symbolic links
            and return attributes for the real path at the base.  If it is 
            False, return attributes for the specified path.
        """
        # lockup filename in utf-8
        path = self.webSafe(path)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        d = defer.maybeDeferred(proc.run, HEAD, path)
        d.addCallback(self._cbGetAttrs)
        d.addErrback(self._cbFailed)
        return d
    
    def _cbGetAttrs(self, obj):
        # check results
        # XXX: not very nice - there is no information about the parent 
        # object in a dict of child objects
        if isinstance(obj, dict):
            return {'permissions': 040755}
        else:
            return {'permissions': 0100644}
    
    def setAttrs(self, path, attrs):
        # lockup filename in utf-8
        path = self.webSafe(path)
        # XXX: args not good to that here!
        if path not in self.create_files.keys():
            return
        (imf, flags) = self.create_files.pop(path)
        # check for creation flag
        if not (flags & FXF_CREAT == FXF_CREAT):
            return
        imf.data.seek(0)
        # create file
        proc = SFTPProcessor(self.env)
        d = defer.maybeDeferred(proc.run, PUT, path, imf.data)
        d.addErrback(self._cbFailed)
        # XXX: IntegrityError
        return d
    
    def removeFile(self, filename):
        """
        Remove the given file.
        
        @param filename: the name of the file as a string.
        """
        # lockup filename in utf-8
        filename = self.webSafe(filename)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        d = defer.maybeDeferred(proc.run, DELETE, filename)
        d.addErrback(self._cbFailed)
        return d
    
    def renameFile(self, oldpath, newpath):
        # lockup filename in utf-8
        oldpath = self.webSafe(oldpath)
        # query the directory via SFTP processor
        proc = SFTPProcessor(self.env)
        destination = self.env.getRestUrl() + newpath
        d = defer.maybeDeferred(proc.run, MOVE, oldpath, 
                                received_headers={'Destination': destination})
        d.addErrback(self._cbFailed)
        return d
    
    def makeDirectory(self, path, attrs):
        msg = "Directories can't be added via SFTP."
        raise SFTPError(FX_OP_UNSUPPORTED, msg)
    
    def removeDirectory(self, path):
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
        attrs['atime'] = s.st_atime = int(attrs.get('atime', 
                                                    self.env.startup_time))
        attrs['mtime'] = s.st_mtime = int(attrs.get('mtime', 
                                                    self.env.startup_time))
        attrs['nlink'] = s.st_nlink = 1
        return ( name, lsLine(name, s), attrs)
    
    def close(self):
        return
