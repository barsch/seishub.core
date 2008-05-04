# -*- coding: utf-8 -*-

import string
from urllib import unquote

from seishub.core import ExtensionPoint
from seishub.services.interfaces import IPackage, IResourceType


class Processor(object):
    """General class for processing a request used by SFTP and REST."""
    
    resourcetype_ids = []
    resourcetypes = {}
    packages = []
    
    def __init__(self, env):
        self.env = env
        self.packages = self.getPackages()
    
    def getPackages(self):
        """Returns sorted dict of all packages."""
        packages = ExtensionPoint(IPackage).extensions(self.env)
        packages = [str(p.getPackageId()) for p in packages 
                    if hasattr(p, 'getPackageId')]
        packages.sort()
        return packages
    
    def getResourceTypes(self, package_id=None):
        """
        Returns sorted dict of all resource types, optional filtered by a 
        package id.
        """
        components = ExtensionPoint(IResourceType).extensions(self.env)
        resourcetype_ids = []
        resourcetypes = {}
        for c in components:
            if not hasattr(c, 'getResourceTypeId'):
                continue
            if package_id and (not hasattr(c, 'getPackageId') or 
                               c.getPackageId()!=package_id):
                continue
            id = str(c.getResourceTypeId())
            resourcetype_ids.append(id)
            resourcetypes[id]=c
        resourcetype_ids.sort()
        return resourcetype_ids, resourcetypes
    
    def process(self):
        """Working through the process chain."""
        # test if root element
        if self.path == '/':
            return self.processRoot()
        # post process self.path
        self.postpath = map(unquote, string.split(self.path[1:], '/'))
        # test if direct resource
        if self.postpath[0]=='seishub':
            return self.processResource()
        # test if a package_id
        self.packages = self.getPackages()
        if self.postpath[0] in self.packages:
            return self.processPackage()
    
    def processRoot(self):
        return self.packages + ['seishub']
    
    def processResource(self):
        """Direct access of a resource."""
        pass
    
    def processPackage(self):
        """
        Request on a package. Now we try to solve valid resource types of this
        package. If this fails we will look for package aliases or package
        mappings defined by the user."""
        
        package_id = self.postpath[0]
        
        # fetch resource types
        ids, comps = self.getResourceTypes(package_id)
        self.resourcetype_ids = ids
        self.resourcetypes = comps

        # test if only package_id is given
        if len(self.postpath)==1:
            return self.resourcetype_ids
        
        # test for resource type
        if self.postpath[1] in self.resourcetype_ids:
            return self.processResourceType()
        
        # test for package aliases
        
        # test for package mappings

    def modifyResource(self, content):
        """Handles a POST request."""
        pass
    
    def addResource(self, content):
        """Handles a PUT request."""
        try:
            res = self.env.catalog.newXmlResource(self.path, content)
            self.env.catalog.addResource(res)
        except Exception, e:
            self.env.log.error(e)
    
    def deleteResource(self):
        """Handles a DELETE request."""
        try:
            self.env.catalog.deleteResource(self.path)
        except Exception, e:
            self.env.log.error(e)
