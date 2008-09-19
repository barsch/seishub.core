# -*- coding: utf-8 -*-


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