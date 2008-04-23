# -*- coding: utf-8 -*-

import os, getpass, struct, tty, fcntl, stat
import fnmatch, pwd, time, glob

from zope.interface import implements
from twisted.cred import portal, checkers
from twisted.conch import avatar, interfaces as conchinterfaces
from twisted.protocols import basic
from twisted.conch.ssh import factory, keys, session, common, filetransfer
from twisted.conch.insults import insults
from twisted.application import internet
from twisted.internet import defer, utils
from twisted.python import log, failure

from seishub import __version__ as SEISHUB_VERSION
from seishub.defaults import SFTP_PORT, SFTP_PRIVATE_KEY, SFTP_PUBLIC_KEY
from seishub.config import IntOption, Option


def _ignore(*args): pass


class FileWrapper:

    def __init__(self, f):
        self.f = f
        self.total = 0.0
        f.seek(0, 2) # seek to the end
        self.size = f.tell()

    def __getattr__(self, attr):
        return getattr(self.f, attr)


class SFTPServiceProtocol(basic.LineReceiver):
    
    ps = 'cftp> '
    delimiter = '\n'
    
    def __init__(self, client, env, f = '~/'):
        print "hier"
        self.env = env
        self.client = client
        self.currentDirectory = ''
        self.file = f
        self.useProgressBar = (not f and 1) or 0
    
    def connectionMade(self):
        self.client.realPath('').addCallback(self._cbSetCurDir)
    
    def _cbSetCurDir(self, path):
        self.currentDirectory = path
        self._newLine()
    
    def lineReceived(self, line):
        if self.client.transport.localClosed:
            return
        log.msg('got line %s' % repr(line))
        line = line.lstrip()
        if not line:
            self._newLine()
            return
        if self.file and line.startswith('-'):
            self.ignoreErrors = 1
            line = line[1:]
        else:
            self.ignoreErrors = 0
        if ' ' in line:
            command, rest = line.split(' ', 1)
            rest = rest.lstrip()
        else:
            command, rest = line, ''
        if command.startswith('!'): # command
            f = self.cmd_EXEC
            rest = (command[1:] + ' ' + rest).strip()
        else:
            command = command.upper()
            log.msg('looking up cmd %s' % command)
            f = getattr(self, 'cmd_%s' % command, None)
        if f is not None:
            d = defer.maybeDeferred(f, rest)
            d.addCallback(self._cbCommand)
            d.addErrback(self._ebCommand)
        else:
            self._ebCommand(failure.Failure(NotImplementedError(
                "No command called `%s'" % command)))
            self._newLine()
            
    def _printFailure(self, f):
        log.msg(f)
        e = f.trap(NotImplementedError, filetransfer.SFTPError, OSError, IOError)
        if e == NotImplementedError:
            self.transport.write(self.cmd_HELP(''))
        elif e == filetransfer.SFTPError:
            self.transport.write("remote error %i: %s\n" % 
                    (f.value.code, f.value.message))
        elif e in (OSError, IOError):
            self.transport.write("local error %i: %s\n" %
                    (f.value.errno, f.value.strerror))
    
    def _newLine(self):
        if self.client.transport.localClosed:
            return
        self.transport.write(self.ps)
        self.ignoreErrors = 0
        if self.file:
            l = self.file.readline()
            if not l:
                self.client.transport.loseConnection()
            else:
                self.transport.write(l)
                self.lineReceived(l.strip())

    def _cbCommand(self, result):
        if result is not None:
            self.transport.write(result)
            if not result.endswith('\n'):
                self.transport.write('\n')
        self._newLine()

    def _ebCommand(self, f):
        self._printFailure(f)
        if self.file and not self.ignoreErrors:
            self.client.transport.loseConnection()
        self._newLine()

    def cmd_CD(self, path):
        path, rest = self._getFilename(path)
        if not path.endswith('/'):
            path += '/'
        newPath = path and os.path.join(self.currentDirectory, path) or ''
        d = self.client.openDirectory(newPath)
        d.addCallback(self._cbCd)
        d.addErrback(self._ebCommand)
        return d

    def _cbCd(self, directory):
        directory.close()
        d = self.client.realPath(directory.name)
        d.addCallback(self._cbCurDir)
        return d

    def _cbCurDir(self, path):
        self.currentDirectory = path

    def cmd_CHGRP(self, rest):
        grp, rest = rest.split(None, 1)
        path, rest = self._getFilename(rest)
        grp = int(grp)
        d = self.client.getAttrs(path)
        d.addCallback(self._cbSetUsrGrp, path, grp=grp)
        return d
    
    def cmd_CHMOD(self, rest):
        mod, rest = rest.split(None, 1)
        path, rest = self._getFilename(rest)
        mod = int(mod, 8)
        d = self.client.setAttrs(path, {'permissions':mod})
        d.addCallback(_ignore)
        return d
    
    def cmd_CHOWN(self, rest):
        usr, rest = rest.split(None, 1)
        path, rest = self._getFilename(rest)
        usr = int(usr)
        d = self.client.getAttrs(path)
        d.addCallback(self._cbSetUsrGrp, path, usr=usr)
        return d
    
    def _cbSetUsrGrp(self, attrs, path, usr=None, grp=None):
        new = {}
        new['uid'] = (usr is not None) and usr or attrs['uid']
        new['gid'] = (grp is not None) and grp or attrs['gid']
        d = self.client.setAttrs(path, new)
        d.addCallback(_ignore)
        return d

    def cmd_GET(self, rest):
        remote, rest = self._getFilename(rest)
        if '*' in remote or '?' in remote: # wildcard
            if rest:
                local, rest = self._getFilename(rest)
                if not os.path.isdir(local):
                    return "Wildcard get with non-directory target."
            else:
                local = ''
            d = self._remoteGlob(remote)
            d.addCallback(self._cbGetMultiple, local)
            return d
        if rest:
            local, rest = self._getFilename(rest)
        else:
            local = os.path.split(remote)[1]
        log.msg((remote, local))
        lf = file(local, 'w', 0)
        path = os.path.join(self.currentDirectory, remote)
        d = self.client.openFile(path, filetransfer.FXF_READ, {})
        d.addCallback(self._cbGetOpenFile, lf)
        d.addErrback(self._ebCloseLf, lf)
        return d

    def _cbGetMultiple(self, files, local):
        #if self._useProgressBar: # one at a time
        # XXX this can be optimized for times w/o progress bar
        return self._cbGetMultipleNext(None, files, local)

    def _cbGetMultipleNext(self, res, files, local):
        if isinstance(res, failure.Failure):
            self._printFailure(res)
        elif res:
            self.transport.write(res)
            if not res.endswith('\n'):
                self.transport.write('\n')
        if not files:
            return
        f = files.pop(0)[0]
        lf = file(os.path.join(local, os.path.split(f)[1]), 'w', 0)
        path = os.path.join(self.currentDirectory, f)
        d = self.client.openFile(path, filetransfer.FXF_READ, {})
        d.addCallback(self._cbGetOpenFile, lf)
        d.addErrback(self._ebCloseLf, lf)
        d.addBoth(self._cbGetMultipleNext, files, local)
        return d

    def _ebCloseLf(self, f, lf):
        lf.close()
        return f

    def _cbGetOpenFile(self, rf, lf):
        return rf.getAttrs().addCallback(self._cbGetFileSize, rf, lf)

    def _cbGetFileSize(self, attrs, rf, lf):
        if not stat.S_ISREG(attrs['permissions']):
            rf.close()
            lf.close()
            return "Can't get non-regular file: %s" % rf.name
        rf.size = attrs['size']
        bufferSize = self.client.transport.conn.options['buffersize']
        numRequests = self.client.transport.conn.options['requests']
        rf.total = 0.0
        dList = []
        chunks = []
        startTime = time.time()
        for i in range(numRequests):            
            d = self._cbGetRead('', rf, lf, chunks, 0, bufferSize, startTime)
            dList.append(d)
        dl = defer.DeferredList(dList, fireOnOneErrback=1)
        dl.addCallback(self._cbGetDone, rf, lf)
        return dl

    def _getNextChunk(self, chunks):
        end = 0
        for chunk in chunks:
            if end == 'eof':
                return # nothing more to get
            if end != chunk[0]:
                i = chunks.index(chunk)
                chunks.insert(i, (end, chunk[0]))
                return (end, chunk[0] - end)
            end = chunk[1]
        bufSize = int(self.client.transport.conn.options['buffersize'])
        chunks.append((end, end + bufSize))
        return (end, bufSize)
   
    def _cbGetRead(self, data, rf, lf, chunks, start, size, startTime):
        if data and isinstance(data, failure.Failure):
            log.msg('get read err: %s' % data)
            reason = data
            reason.trap(EOFError)
            i = chunks.index((start, start + size))
            del chunks[i]
            chunks.insert(i, (start, 'eof'))
        elif data:
            log.msg('get read data: %i' % len(data))
            lf.seek(start)
            lf.write(data)
            if len(data) != size:
                log.msg('got less than we asked for: %i < %i' % 
                        (len(data), size))
                i = chunks.index((start, start + size))
                del chunks[i]
                chunks.insert(i, (start, start + len(data)))
            rf.total += len(data)
        if self.useProgressBar:
            self._printProgessBar(rf, startTime)
        chunk = self._getNextChunk(chunks)
        if not chunk:
            return
        else:
            start, length = chunk
        log.msg('asking for %i -> %i' % (start, start+length))
        d = rf.readChunk(start, length)
        d.addBoth(self._cbGetRead, rf, lf, chunks, start, length, startTime)
        return d

    def _cbGetDone(self, ignored, rf, lf):
        log.msg('get done')
        rf.close()
        lf.close()
        if self.useProgressBar:
            self.transport.write('\n')
        return "Transferred %s to %s" % (rf.name, lf.name)
   
    def cmd_PUT(self, rest):
        local, rest = self._getFilename(rest)
        if '*' in local or '?' in local: # wildcard
            if rest:
                remote, rest = self._getFilename(rest)
                path = os.path.join(self.currentDirectory, remote)
                d = self.client.getAttrs(path)
                d.addCallback(self._cbPutTargetAttrs, remote, local)
                return d
            else:
                remote = ''
                files = glob.glob(local)
                return self._cbPutMultipleNext(None, files, remote)
        if rest:
            remote, rest = self._getFilename(rest)
        else:
            remote = os.path.split(local)[1]
        lf = file(local, 'r')
        path = os.path.join(self.currentDirectory, remote)
        d = self.client.openFile(path, filetransfer.FXF_WRITE|filetransfer.FXF_CREAT, {})
        d.addCallback(self._cbPutOpenFile, lf)
        d.addErrback(self._ebCloseLf, lf)
        return d

    def _cbPutTargetAttrs(self, attrs, path, local):
        if not stat.S_ISDIR(attrs['permissions']):
            return "Wildcard put with non-directory target."
        return self._cbPutMultipleNext(None, files, path)

    def _cbPutMultipleNext(self, res, files, path):
        if isinstance(res, failure.Failure):
            self._printFailure(res)
        elif res:
            self.transport.write(res)
            if not res.endswith('\n'):
                self.transport.write('\n')
        f = None
        while files and not f:
            try: 
                f = files.pop(0)
                lf = file(f, 'r')
            except:
                self._printFailure(failure.Failure())
                f = None
        if not f:
            return
        name = os.path.split(f)[1]
        remote = os.path.join(self.currentDirectory, path, name)
        log.msg((name, remote, path))
        d = self.client.openFile(remote, filetransfer.FXF_WRITE|filetransfer.FXF_CREAT, {})
        d.addCallback(self._cbPutOpenFile, lf)
        d.addErrback(self._ebCloseLf, lf)
        d.addBoth(self._cbPutMultipleNext, files, path)
        return d

    def _cbPutOpenFile(self, rf, lf):
        numRequests = self.client.transport.conn.options['requests']
        if self.useProgressBar:
            lf = FileWrapper(lf)
        dList = []
        chunks = []
        startTime = time.time()
        for i in range(numRequests):
            d = self._cbPutWrite(None, rf, lf, chunks, startTime)
            if d:
                dList.append(d)
        dl = defer.DeferredList(dList, fireOnOneErrback=1)
        dl.addCallback(self._cbPutDone, rf, lf)
        return dl

    def _cbPutWrite(self, ignored, rf, lf, chunks, startTime):
        chunk = self._getNextChunk(chunks)
        start, size = chunk
        lf.seek(start)
        data = lf.read(size)
        if self.useProgressBar:
            lf.total += len(data)
            self._printProgessBar(lf, startTime)
        if data:
            d = rf.writeChunk(start, data)
            d.addCallback(self._cbPutWrite, rf, lf, chunks, startTime)
            return d
        else:
            return

    def _cbPutDone(self, ignored, rf, lf):
        lf.close()
        rf.close()
        if self.useProgressBar:
            self.transport.write('\n')
        return 'Transferred %s to %s' % (lf.name, rf.name)

    def cmd_LCD(self, path):
        os.chdir(path)

    def cmd_LN(self, rest):
        linkpath, rest = self._getFilename(rest)
        targetpath, rest = self._getFilename(rest)
        linkpath, targetpath = map(
                lambda x: os.path.join(self.currentDirectory, x),
                (linkpath, targetpath))
        return self.client.makeLink(linkpath, targetpath).addCallback(_ignore)

    def cmd_LS(self, rest):
        # possible lines:
        # ls                    current directory
        # ls name_of_file       that file
        # ls name_of_directory  that directory
        # ls some_glob_string   current directory, globbed for that string
        options = []
        rest = rest.split()
        while rest and rest[0] and rest[0][0] == '-':
            opts = rest.pop(0)[1:]
            for o in opts:
                if o == 'l':
                    options.append('verbose')
                elif o == 'a':
                    options.append('all')
        rest = ' '.join(rest)
        path, rest = self._getFilename(rest)
        if not path:
            fullPath = self.currentDirectory + '/'
        else:
            fullPath = os.path.join(self.currentDirectory, path)
        d = self._remoteGlob(fullPath)
        d.addCallback(self._cbDisplayFiles, options)
        return d

    def _cbDisplayFiles(self, files, options):
        files.sort()
        if 'all' not in options:
            files = [f for f in files if not f[0].startswith('.')]
        if 'verbose' in options:
            lines = [f[1] for f in files]
        else:
            lines = [f[0] for f in files]
        if not lines:
            return None
        else:
            return '\n'.join(lines)

    def cmd_MKDIR(self, path):
        path, rest = self._getFilename(path)
        path = os.path.join(self.currentDirectory, path)
        return self.client.makeDirectory(path, {}).addCallback(_ignore)

    def cmd_RMDIR(self, path):
        path, rest = self._getFilename(path)
        path = os.path.join(self.currentDirectory, path)
        return self.client.removeDirectory(path).addCallback(_ignore)

    def cmd_LMKDIR(self, path):
        os.system("mkdir %s" % path)

    def cmd_RM(self, path):
        path, rest = self._getFilename(path)
        path = os.path.join(self.currentDirectory, path)
        return self.client.removeFile(path).addCallback(_ignore)

    def cmd_LLS(self, rest):
        os.system("ls %s" % rest)

    def cmd_RENAME(self, rest):
        oldpath, rest = self._getFilename(rest)
        newpath, rest = self._getFilename(rest)
        oldpath, newpath = map (
                lambda x: os.path.join(self.currentDirectory, x),
                (oldpath, newpath))
        return self.client.renameFile(oldpath, newpath).addCallback(_ignore)

    def cmd_EXIT(self, ignored):
        self.client.transport.loseConnection()

    cmd_QUIT = cmd_EXIT

    def cmd_VERSION(self, ignored):
        return "SeisHub SFTP version %s" % SEISHUB_VERSION
    
    def cmd_HELP(self, ignored):
        return """Available commands:
cd path                         Change remote directory to 'path'.
chgrp gid path                  Change gid of 'path' to 'gid'.
chmod mode path                 Change mode of 'path' to 'mode'.
chown uid path                  Change uid of 'path' to 'uid'.
exit                            Disconnect from the server.
get remote-path [local-path]    Get remote file.
help                            Get a list of available commands.
lcd path                        Change local directory to 'path'.
lls [ls-options] [path]         Display local directory listing.
lmkdir path                     Create local directory.
ln linkpath targetpath          Symlink remote file.
lpwd                            Print the local working directory.
ls [-l] [path]                  Display remote directory listing.
mkdir path                      Create remote directory.
progress                        Toggle progress bar.
put local-path [remote-path]    Put local file.
pwd                             Print the remote working directory.
quit                            Disconnect from the server.
rename oldpath newpath          Rename remote file.
rmdir path                      Remove remote directory.
rm path                         Remove remote file.
version                         Print the SFTP version.
?                               Synonym for 'help'.
"""

    def cmd_PWD(self, ignored):
        return self.currentDirectory

    def cmd_LPWD(self, ignored):
        return os.getcwd()

    def cmd_PROGRESS(self, ignored):
        self.useProgressBar = not self.useProgressBar
        return "%ssing progess bar." % (self.useProgressBar and "U" or "Not u")

    def cmd_EXEC(self, rest):
        shell = pwd.getpwnam(getpass.getuser())[6]
        print repr(rest)
        if rest:
            cmds = ['-c', rest]
            return utils.getProcessOutput(shell, cmds, errortoo=1)
        else:
            os.system(shell)

    # accessory functions

    def _remoteGlob(self, fullPath):
        log.msg('looking up %s' % fullPath)
        head, tail = os.path.split(fullPath)
        if '*' in tail or '?' in tail:
            glob = 1
        else:
            glob = 0
        if tail and not glob: # could be file or directory
           # try directory first
           d = self.client.openDirectory(fullPath)
           d.addCallback(self._cbOpenList, '')
           d.addErrback(self._ebNotADirectory, head, tail)
        else:
            d = self.client.openDirectory(head)
            d.addCallback(self._cbOpenList, tail)
        return d

    def _cbOpenList(self, directory, glob):
        files = []
        d = directory.read()
        d.addBoth(self._cbReadFile, files, directory, glob)
        return d

    def _ebNotADirectory(self, reason, path, glob):
        d = self.client.openDirectory(path)
        d.addCallback(self._cbOpenList, glob)
        return d

    def _cbReadFile(self, files, l, directory, glob):
        if not isinstance(files, failure.Failure):
            if glob:
                l.extend([f for f in files if fnmatch.fnmatch(f[0], glob)])
            else:
                l.extend(files)
            d = directory.read()
            d.addBoth(self._cbReadFile, l, directory, glob)
            return d
        else:
            reason = files
            reason.trap(EOFError)
            directory.close()
            return l

    def _abbrevSize(self, size):
        # from http://mail.python.org/pipermail/python-list/1999-December/018395.html
        _abbrevs = [
            (1<<50L, 'PB'),
            (1<<40L, 'TB'), 
            (1<<30L, 'GB'), 
            (1<<20L, 'MB'), 
            (1<<10L, 'kb'),
            (1, '')
            ]

        for factor, suffix in _abbrevs:
            if size > factor:
                break
        return '%.1f' % (size/factor) + suffix

    def _abbrevTime(self, t):
        if t > 3600: # 1 hour
            hours = int(t / 3600)
            t -= (3600 * hours)
            mins = int(t / 60)
            t -= (60 * mins)
            return "%i:%02i:%02i" % (hours, mins, t)
        else:
            mins = int(t/60)
            t -= (60 * mins)
            return "%02i:%02i" % (mins, t)

    def _printProgessBar(self, f, startTime):
        diff = time.time() - startTime
        total = f.total
        try:
            winSize = struct.unpack('4H', 
                fcntl.ioctl(0, tty.TIOCGWINSZ, '12345679'))
        except IOError:
            winSize = [None, 80]
        speed = total/diff
        if speed:
            timeLeft = (f.size - total) / speed
        else:
            timeLeft = 0
        front = f.name
        back = '%3i%% %s %sps %s ' % ((total/f.size)*100, self._abbrevSize(total),
                self._abbrevSize(total/diff), self._abbrevTime(timeLeft))
        spaces = (winSize[1] - (len(front) + len(back) + 1)) * ' '
        self.transport.write('\r%s%s%s' % (front, spaces, back)) 

    def _getFilename(self, line):
        line.lstrip()
        if not line:
            return None, ''
        if line[0] in '\'"':
            ret = []
            line = list(line)
            try:
                for i in range(1,len(line)):
                    c = line[i]
                    if c == line[0]:
                        return ''.join(ret), ''.join(line[i+1:]).lstrip()
                    elif c == '\\': # quoted character
                        del line[i]
                        if line[i] not in '\'"\\':
                            raise IndexError, "bad quote: \\%s" % line[i]
                        ret.append(line[i])
                    else:
                        ret.append(line[i])
            except IndexError:
                raise IndexError, "unterminated quote"
        ret = line.split(None, 1)
        if len(ret) == 1:
            return ret[0], ''
        else:
            return ret


class SFTPServiceAvatar(avatar.ConchUser):
    implements(conchinterfaces.ISession)
    
    def __init__(self, username, env):
        avatar.ConchUser.__init__(self)
        self.username = username
        self.env = env
        self.channelLookup.update({'session': session.SSHSession})
    
    def openShell(self, protocol):
        serverProtocol = insults.ServerProtocol(SFTPServiceProtocol, self, self.env)
        serverProtocol.makeConnection(protocol)
        protocol.makeConnection(session.wrapProtocol(serverProtocol))
    
    def getPty(self, terminal, windowSize, attrs):
        return None
    
    def execCommand(self, protocol, cmd):
        raise NotImplementedError
    
    def closed(self):
        pass


class SFTPServiceRealm:
    implements(portal.IRealm)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if conchinterfaces.IConchUser in interfaces:
            return interfaces[0], SFTPServiceAvatar(avatarId, self.env), lambda: None
        else:
            raise Exception, "No supported interfaces found."


class SFTPServiceFactory(factory.SSHFactory):
    """Factory for SFTP Server."""
    
    def __init__(self, env):
        self.env = env
        users = {'admin': 'aaa', }
        realm = SFTPServiceRealm(env)
        check = [checkers.InMemoryUsernamePasswordDatabaseDontUse(**users)]
        self.portal = portal.Portal(realm, check)
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
