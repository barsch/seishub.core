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
    