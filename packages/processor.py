# -*- coding: utf-8 -*-

import string

from urllib import unquote
from twisted.web import http

from seishub.util.text import isInteger 


class Processor(object):
    """General class for processing a request used by SFTP and REST."""
    
    resourcetypes = {}
    packages = []
    package_id = None
    resourcetype_id = None
    
    def __init__(self, env):
        self.env = env
        self.package_ids = self.env.registry.getPackageIds()
    
    def process(self):
        """Working through the process chain."""
        # check if correct method
        if self.method not in ['GET','PUT','POST','DELETE']:
            return self.formatError(http.NOT_ALLOWED)
        # post process self.path
        self.postpath = filter(len, 
                               map(unquote, string.split(self.path[1:], '/')))
        # test if root element
        if len(self.postpath)==0:
            if self.method=='GET':
                return self.processRoot()
            else:
                return self.formatError(http.NOT_ALLOWED)
        
        # test if valid package_id
        if self.postpath[0] not in self.package_ids:
            return self.formatError(http.NOT_FOUND)
        else:
            self.package_id = self.postpath[0]
        # if only package_id is requested
        if len(self.postpath)==1:
            if self.method=='GET':
                return self.processPackage()
            else:
                return self.formatError(http.NOT_ALLOWED)
        
        # fetch package aliases
        alias_ids = []
        # its may be an package alias
        if len(self.postpath)==2 and self.postpath[1] in alias_ids:
            return self.processAlias()
        
        # fetch resource types
        resourcetypes = self.env.registry.getResourceTypes(self.package_id)
        resourcetype_ids = resourcetypes.keys()
        resourcetype_ids.sort()
        # test if valid resourcetype_id
        if self.postpath[1] not in resourcetype_ids:
            return self.formatError(http.NOT_FOUND)
        else:
            self.resourcetype_id = self.postpath[1] 
        # we may have a direct resource
        if len(self.postpath)==3 and isInteger(self.postpath[2]):
            return self.processResource()
        # only package_id + resourcetype_id should be a GET request
        if len(self.postpath)==2 and self.method!='GET':
            return self.formatError(http.NOT_ALLOWED)
        # now only mappings and aliases are left ...
        return self.processResourcetype()
    
    def processRoot(self):
        """
        The root element can be only accessed via the GET method and shows a 
        list of all packages.
        """
        return self.formatResourceList(self.package_ids)
    
    def processPackage(self):
        """
        Request on a package. Now we search all valid resource types of this
        package. If this fails we will look for all defined package aliases and 
        add them to the list.
        """
        # fetch resource types
        resourcetypes = self.env.registry.getResourceTypes(self.package_id)
        resourcetype_ids = resourcetypes.keys()
        # fetch package aliases
        alias_ids = []
        list = alias_ids + resourcetype_ids
        list.sort()
        return self.formatResourceList(list, '/'+self.package_id)
    
    def processResourceTypes(self):
        """
        Request on a certain resource type of a package. Now we try to solve 
        for resource type aliases or package mappings defined by the user. Also
        we add a few special hardcoded aliases.
        """
        # fetch resourcetype aliases
        alias_ids = []
        # fetch resourcetype mappings
        mapping_ids = []
        # test if only package_id and resourcetype_id is given
        if len(self.postpath)==2:
            list = alias_ids + mapping_ids
            return self.formatResourceList(list, '/'+self.package_id+
                                                 '/'+self.resourcetype_id)
        # now only aliases nd mappings are left
        if len(self.postpath)==3:
            # test if mapping
            if self.postpath[2] in mapping_ids:
                return self.processMapping()
            # test if alias
            if self.postpath[2] in alias_ids:
                return self.processAlias()
        return self.formatError(http.NOT_FOUND)
    
    def processResource(self):
        """
        Direct access on a resource consists always of a package_id, 
        resourcetype_id and an integer as document_id.
        """
        if self.method=='GET':
            return self.getResource()
        if self.method=='POST':
            return self.modifyResource()
        elif self.method=='PUT':
            return self.createResource()
        elif self.method=='DELETE':
            return self.deleteResource()
    
    def processMapping(self):
        pass
    
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
    
    def formatResourceList(self, uris, baseuri):
        """Resource list handler for the inheriting class."""
        assert 0, 'formatResourceList must be defined'
    
    def formatResource(self, uris, baseuri):
        """Resource handler for the inheriting class."""
        assert 0, 'formatResource must be defined'
    
    def formatError(self, error_id, msg=None):
        """Error handler for the inheriting class."""
        assert 0, 'formatError must be defined'
