# -*- coding: utf-8 -*-
import os,sys

def getRelativePath(path1,path2=sys.path[0]):
    path1=os.path.abspath(path1)
    path2=os.path.abspath(path2)
    if path1.startswith(path2):
        return path1[len(path2)+1:]
    elif path2.startswith(path1):
        return path2[len(path1)+1:]

def rglob(base_path=sys.path[0],search_path=sys.path[0],ext=""):
    ext_files=[]
    
    def ls(arg,dirname,files):
        dirname=getRelativePath(dirname,base_path)
        ext_files.extend([os.path.join(dirname,i) for i in files if i.endswith(ext)])
    
    os.path.walk(search_path,ls,"")
    return ext_files

def getAbsoluteSegments(path, cwd='/'):
    """
    @param path: either a string or a list of string segments
    which specifys the desired path.  may be relative to the cwd
    
    @param cwd: optional string specifying the current working directory
    
    returns a list of string segments which most succinctly
    describe how to get to path from root
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

def absPath(path):
    return "/" + "/".join(splitPath(path))

def splitPath(path):
    return getAbsoluteSegments(path)