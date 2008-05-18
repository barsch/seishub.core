# -*- coding: utf-8 -*-

import string

from urllib import unquote
from twisted.web import http


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
        # test if root element
        if self.path == '/' and self.method=='GET':
            return self.processRoot()
        # post process self.path
        self.postpath = filter(len, 
                               map(unquote, string.split(self.path[1:], '/')))
        # test if direct resource
        if self.postpath[0]=='seishub':
            return self.processResource()
        # test if a predefined package_id
        if self.postpath[0] in self.package_ids:
            return self.processPackage()
        # everything else should not be processed
        return self.formatError(http.NOT_ALLOWED)
    
    def processRoot(self):
        """
        The root element can be only browsed via GET method and shows a list 
        of all packages and the extra entry 'seishub', which points to the 
        resources directly.
        """
        return self.formatResourceList(self.package_ids + ['seishub'])
    
    def processResource(self):
        """
        Direct access on a resource starts always with the base url '/seishub', 
        followed by package_id and resource_id.
        """
        # check if correct method
        if self.method not in ['GET','PUT','POST','DELETE']:
            return self.formatError(http.NOT_IMPLEMENTED)
        # only GETs may browse through the tree
        if len(self.postpath)<3 and self.method!='GET':
            self.returnError(http.NOT_ALLOWED)
        # POST, PUT and DELETE can be handled directly now
        if self.method=='POST':
            return self.modifyResource()
        elif self.method=='PUT':
            return self.createResource()
        elif self.method=='DELETE':
            return self.deleteResource()
        # only GET requests are left
        # just '/seishub' is given
        if len(self.postpath)==1:
            return self.formatResourceList(self.package_ids, '/seishub')
        # '/seishub' and a package_id is given
        if len(self.postpath)==2 and self.postpath[1] in self.package_ids:
            # fetch only resource types
            resourcetypes = self.env.registry.getResourceTypes(self.package_id)
            resourcetype_ids = resourcetypes.keys()
            resourcetype_ids.sort()
            return self.formatResourceList(resourcetype_ids, 
                                           '/seishub/'+self.postpath[1])
        return self.getResource()
    
    def processPackage(self):
        """
        Request on a package. Now we try to solve valid resource types of this
        package. If this fails we will look for package aliases or package
        mappings defined by the user.
        """
        self.package_id = self.postpath[0]
        # fetch resource types
        self.resourcetypes = self.env.registry.getResourceTypes(self.package_id)
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
