# -*- coding: utf-8 -*-

import array
import stat
import time


def lsLine(name, s):
    """Plain copy and bugfix of twisted.conch.ls.lsLine."""
    mode = s.st_mode
    perms = array.array('c', '-'*10)
    ft = stat.S_IFMT(mode)
    if stat.S_ISDIR(ft): perms[0] = 'd'
    elif stat.S_ISCHR(ft): perms[0] = 'c'
    elif stat.S_ISBLK(ft): perms[0] = 'b'
    elif stat.S_ISREG(ft): perms[0] = '-'
    elif stat.S_ISFIFO(ft): perms[0] = 'f'
    elif stat.S_ISLNK(ft): perms[0] = 'l'
    elif stat.S_ISSOCK(ft): perms[0] = 's'
    else: perms[0] = '!'
    # user
    if mode&stat.S_IRUSR:perms[1] = 'r'
    if mode&stat.S_IWUSR:perms[2] = 'w'
    if mode&stat.S_IXUSR:perms[3] = 'x'
    # group
    if mode&stat.S_IRGRP:perms[4] = 'r'
    if mode&stat.S_IWGRP:perms[5] = 'w'
    if mode&stat.S_IXGRP:perms[6] = 'x'
    # other
    if mode&stat.S_IROTH:perms[7] = 'r'
    if mode&stat.S_IWOTH:perms[8] = 'w'
    if mode&stat.S_IXOTH:perms[9] = 'x'
    # suid/sgid
    if mode&stat.S_ISUID:
        if perms[3] == 'x': perms[3] = 's'
        else: perms[3] = 'S'
    if mode&stat.S_ISGID:
        if perms[6] == 'x': perms[6] = 's'
        else: perms[6] = 'S'
    l = perms.tostring()
    l += str(s.st_nlink).rjust(5) + ' '
    un = str(s.st_uid)
    l += un.ljust(9)
    gr = str(s.st_gid)
    l += gr.ljust(9)
    sz = str(s.st_size)
    l += sz.rjust(8)
    l += ' '
    sixmo = 60 * 60 * 24 * 7 * 26
    if s.st_mtime + sixmo < time.time(): # last edited more than 6mo ago
        # bugfix
        # l += time.strftime("%b %2d  %Y ", time.localtime(s.st_mtime))
        l += time.strftime("%b %d  %Y ", time.localtime(s.st_mtime))
    else:
        # bugfix
        # l += time.strftime("%b %2d  %Y ", time.localtime(s.st_mtime))
        l += time.strftime("%b %d %H:%S ", time.localtime(s.st_mtime))
    l += name
    return l


def getAbsoluteSegments(path, cwd='/'):
    """
    @param path: either a string or a list of string segments
    which specifys the desired path.  may be relative to the cwd
    
    @param cwd: optional string specifying the current working directory
    
    returns a list of string segments which most succinctly
    describe how to get to path from root.
    
    @organization: Twisted Matrix Labs
    @see: U{http://twistedmatrix.com/trac/browser/tags/releases/twisted-8.1.0/twisted/vfs/pathutils.py}
    @copyright: MIT license U{http://en.wikipedia.org/wiki/MIT_License}
    @contact: U{Andy Gayton<mailto:andy@thecablelounge.com>}
    """
    if not isinstance(path, list): paths = path.split("/")
    else: paths = path
    
    if len(paths) and paths[0] == "":
        paths = paths[1:]
    else:
        paths = cwd.split("/") + paths
    
    result = []
    
    for path in paths:
        if path == "..":
            if len(result) > 1:
                result = result[:-1]
            else:
                result = []
        
        elif path not in ("", "."):
            result.append(path)
    
    return result


def splitPath(path):
    """Split a path in segments returning a list."""
    return getAbsoluteSegments(path)


def absPath(path):
    """Returns the absolute path."""
    return "/" + "/".join(splitPath(path))


def addBaseToList(base='/', items=[]):
    """Adds a base path to each single element of a list."""
    if not base.startswith('/'):
        base = '/' + base
    if not base.endswith('/'):
        base = base + '/'
    return [base + i for i in items]