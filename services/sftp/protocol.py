# -*- coding: utf-8 -*-

from seishub.exceptions import InternalServerError, ForbiddenError, \
    NotFoundError, DuplicateObjectError, SeisHubError
from seishub.processor import Processor, PUT, DELETE, GET, MOVE, HEAD, \
    getChildForRequest, POST
from seishub.processor.interfaces import IFileSystemResource, IStatical, \
    IResource, IScriptResource, IRESTResource
from seishub.util.path import absPath
from twisted.conch.interfaces import ISFTPFile, ISFTPServer
from twisted.conch.ls import lsLine
from twisted.conch.ssh.filetransfer import SFTPError, FX_FAILURE, \
    FX_OP_UNSUPPORTED, FXF_READ, FXF_WRITE, FXF_CREAT, FX_NO_SUCH_FILE, \
    FX_FILE_ALREADY_EXISTS
from zope.interface import implements
import StringIO
import sys


DEFAULT_GID = 1000
DEBUG = False


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
        if DEBUG:
            print "--> IMF.init", filename, flags, attrs
        self.filename = filename
        self.flags = flags
        self.attrs = attrs
        self.env = env
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
        if DEBUG:
            print "--> IMF.readChunk", offset, length
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
        if DEBUG:
            print "--> IMF.writeChunk", offset, len(data)
        self.data.seek(offset)
        self.data.write(data)
    
    def close(self):
        """
        Close the file.

        This method returns nothing if the close succeeds immediately, or a
        Deferred that is called back when the close succeeds.
        """
        if DEBUG:
            print "--> IMF.close", self.filename
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
        print self.flags
        proc = SFTPProcessor(self.env)
        #import pdb;pdb.set_trace()
        try:
            # new resource
            proc.run(PUT, self.filename, self.data)
        except SeisHubError, e:
            raise SFTPError(FX_FAILURE, e.message)
        except Exception,e:
            raise
    
    def getAttrs(self):
        """
        Return the attributes for the file.
        
        This method returns a dictionary in the same format as the attrs
        argument to L{openFile} or a L{Deferred} that is called back with same.
        """
        if DEBUG:
            print "--> IMF.getAttrs"
        return {}
    
    def setAttrs(self, attrs):
        """
        Set the attributes for the file.
        
        This method returns when the attributes are set or a Deferred that is
        called back when they are.
        
        @param attrs: a dictionary in the same format as the attrs argument to
        L{openFile}.
        """
        if DEBUG:
            print "--> IMF.setAttrs", attrs
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
        if DEBUG:
            print "--> realPath", path
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
        if DEBUG:
            print "--> openFile", filename, flags, attrs
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
        if DEBUG:
            print "--> openDirectory", path
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
        if DEBUG:
            print "--> getAttrs", path, followLinks
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
        if DEBUG:
            print "--> setAttrs", path, attrs
        return
    
    def removeFile(self, filename):
        """
        Remove the given file.
        
        This method returns when the remove succeeds, or a Deferred that is
        called back when it succeeds.
        
        @param filename: the name of the file as a string.
        """
        if DEBUG:
            print "--> removeFile", filename
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
        if DEBUG:
            print "--> renameFile", oldpath, newpath
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
        if DEBUG:
            print "--> DirList.__init__", iter
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
