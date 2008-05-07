# -*- coding: utf-8 -*-

import string
import os

from urllib import unquote
from pkg_resources import resource_filename #@UnresolvedImport 

from seishub.util.xml import XmlTreeDoc, XmlStylesheet
from seishub.core import ExtensionPoint, PackageManager
from seishub.services.interfaces import IPackage, IResourceType


class Processor(object):
    """General class for processing a request used by SFTP and REST."""
    
    resourcetypes = {}
    packages = []
    package_id = None
    resourcetype_id = None
    
    def __init__(self, env):
        self.env = env
        self.packages = self.getPackages()
    
    def getPackages(self):
        """Returns sorted dict of all packages."""
        # XXX: IMO there is no need for a special PackageManager.getEnabledPackages()
        # function from a performance point of view, as no overhead is generated
        # by the following code (besides inactive but enabled packages become activated),
        # though it might be convenient to have one,
        # in that case we would have to lift the IPackage interface to core level,
        # to make it available to the PackageManager
        # see also the comments on PackageManager in seishub.core
         
        packages = ExtensionPoint(IPackage).extensions(self.env)
        packages = [str(p.package_id) for p in packages]
#        packages = PackageManager.getPackageIds(self.env)
        packages.sort()
        return packages
    
    def getResourceTypes(self, package_id=None):
        """
        Returns sorted dict of all resource types, optional filtered by a 
        package id.
        """
        # XXX: This should be done via a registry!!!
        
#        components = ExtensionPoint(IResourceType).extensions(self.env)
#        resourcetypes = {}
#        for c in components:
#            if not hasattr(c, 'getResourceTypeId'):
#                continue
#            if package_id and (not hasattr(c, 'getPackageId') or 
#                               c.getPackageId()!=package_id):
#                continue
#            id = str(c.getResourceTypeId())
#            resourcetypes[id]=c
        components = PackageManager.getComponents(IResourceType, package_id, 
                                                  self.env)
        resourcetypes = {}
        for c in components:
            id = c.getResourceTypeId()
            resourcetypes[id] = c
            
        return resourcetypes
    
    def process(self):
        """Working through the process chain."""
        # test if root element
        if self.path == '/' and self.method=='GET':
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
        # return NotImplementedYet
    
    def processRoot(self):
        return self.formatResourceList(self.packages + ['seishub'])
    
    def processResource(self):
        """Direct access on a resource."""
        
        # test if only 'seishub' is given
        if len(self.postpath)==1 and self.method=='GET':
            return self.formatResourceList(self.packages, '/seishub')
        # test for method
        if self.method=='GET':
            return self.getResource()
        if self.method=='POST':
            return self.modifyResource()
        if self.method=='PUT':
            return self.createResource()
        if self.method=='DELETE':
            return self.deleteResource()
    
    def processPackage(self):
        """
        Request on a package. Now we try to solve valid resource types of this
        package. If this fails we will look for package aliases or package
        mappings defined by the user.
        """
        
        self.package_id = self.postpath[0]
        
        # fetch resource types
        self.resourcetypes = self.getResourceTypes(self.package_id)
        resourcetype_ids = self.resourcetypes.keys()
        resourcetype_ids.sort()
        
        # test if only package_id is given
        if len(self.postpath)==1 and self.method=='GET':
            return self.formatResourceList(resourcetype_ids, 
                                           '/'+self.package_id)
        # test for resource type
        if self.postpath[1] in resourcetype_ids:
            return self.processResourceType()
        # test for package aliases
        if self.method=='GET' and self.path in self.env.catalog.aliases:
            return self.processAlias()
        # test for package mappings
        return self.processMapping()
    
    def processResourceTypes(self):
        """
        Request on a certain resource type of a package. Now we try to solve 
        for resource type aliases or package mappings defined by the user.
        """
        self.resourcetype_id = self.postpath[1]
        
        # fetch aliases
        
        # fetch mappings
        
        # test if only package_id and resourcetype_id is given
        if len(self.postpath)==2:
            return 
        
        pass
    
    def formatResourceList(self, uris, baseuri):
        assert 0, 'formatResourceList must be defined'
    
    def processAlias(self):
        """Generates a list of resources from an alias query."""
        # fetch list of uris via catalog
        try:
            uris = self.env.catalog.query(self.env.catalog.aliases[self.path])
        except Exception, e:
            self.env.log.error(e)
            return
        return self.formatResourceList(uris)
    
    def getResource(self):
        """Handles a GET request."""
        resource_id = self.path[8:]
        try:
            result = self.env.catalog.getResource(uri = resource_id)
        except Exception, e:
            self.env.log.debug(e)
            return
        try:
            result = result.getData()
            result = result.encode("utf-8")
        except Exception, e:
            self.env.log.error(e)
            return
        return result
    
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
            return
    
    def deleteResource(self):
        """Handles a DELETE request."""
        try:
            self.env.catalog.deleteResource(self.path)
        except Exception, e:
            self.env.log.error(e)
            return
