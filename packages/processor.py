# -*- coding: utf-8 -*-

import string

from urllib import unquote
from twisted.web import http

from seishub.util.text import isInteger 
from seishub.core import SeisHubError


class RequestError(SeisHubError):
    pass


class Processor:
    """
    General class for processing a resource request used SeisHub services, like
    REST or SFTP.
    """
    resourcetypes = {}
    packages = []
    package_id = None
    resourcetype_id = None
    
    def __init__(self, env):
        self.env = env
        self.package_ids = self.env.registry.getPackageIds()
        self.package_ids.sort()
    
    def process(self):
        """Working through the process chain."""
        # check if correct method
        if self.method not in ['GET','PUT','POST','DELETE']:
            raise RequestError(http.NOT_ALLOWED)
        # post process self.path
        self.postpath = filter(len, 
                               map(unquote, string.split(self.path[1:], '/')))
        # test if root element
        if len(self.postpath)==0:
            if self.method=='GET':
                return self._processRoot()
            raise RequestError(http.NOT_ALLOWED)
        
        # XXX: test if a property request
        
        # test if valid package_id
        if self.postpath[0] not in self.package_ids:
            raise RequestError(http.NOT_FOUND)
        else:
            self.package_id = self.postpath[0]
        # if only package_id is requested
        if len(self.postpath)==1:
            if self.method=='GET':
                return self._processPackage()
            raise RequestError(http.NOT_ALLOWED)
        
        # fetch package aliases XXX: missing
        alias_ids = []
        # its may be an package alias
        if len(self.postpath)==2 and self.postpath[1] in alias_ids:
            return self._processAlias()
        
        # fetch resource types
        resourcetypes = self.env.registry.getResourceTypes(self.package_id)
        resourcetype_ids = resourcetypes.keys()
        resourcetype_ids.sort()
        # test if valid resourcetype_id
        if self.postpath[1] not in resourcetype_ids:
            raise RequestError(http.NOT_FOUND)
        else:
            self.resourcetype_id = self.postpath[1]
        # check if a PUT request were called in a resourcetype directory 
        if len(self.postpath)==2 and self.method=='PUT':
            return self._addResource()
        # we may have a direct resource
        if len(self.postpath)==3 and isInteger(self.postpath[2]):
            return self._processResource()
        # only package_id + resourcetype_id should be a GET request
        if len(self.postpath)==2 and self.method!='GET':
            raise RequestError(http.NOT_ALLOWED)
        # now only mappings and aliases are left ...
        return self._processResourceType()
    
    def _processRoot(self):
        """
        The root element can be only accessed via the GET method and shows only
        a list of all packages.
        """
        return self.renderResourceList(package=self.package_ids)
    
    def _processPackage(self):
        """
        Request on a package. Now we search all valid resource types of this
        package. If this fails we will look for all defined package aliases and 
        add them to the list.
        """
        # fetch resource types
        resourcetypes = self.env.registry.getResourceTypes(self.package_id)
        resourcetype_ids = resourcetypes.keys()
        resourcetype_ids.sort()
        # fetch package aliases
        aliases = self.env.registry.aliases.get(self.package_id)
        alias_ids = [alias.name for alias in aliases]
        alias_ids.sort()
        return self.renderResourceList(alias=alias_ids,
                                       resourcetype=resourcetype_ids)
    
    def _processResourceType(self):
        """
        Request on a certain resource type of a package. Now we try to solve 
        for resource type aliases or package mappings defined by the user. Also
        we add a few special hardcoded aliases.
        """
        # fetch resourcetype aliases
        aliases = self.env.registry.aliases.get(self.package_id,
                                                self.resourcetype_id)
        alias_ids = [alias.name for alias in aliases]
        alias_ids.sort()
        # fetch resourcetype mappings XXX: missing
        mapping_ids = []
        mapping_ids.sort()
        # test if only package_id and resourcetype_id is given
        if len(self.postpath)==2:
            return self.renderResourceList(alias=alias_ids, 
                                           mapping=mapping_ids)
        # now only aliases and mappings are left
        if len(self.postpath)==3:
            # test if mapping
            if self.postpath[2] in mapping_ids:
                return self._processMapping()
            # test if alias
            if self.postpath[2] in alias_ids:
                return self._processAlias()
            # test if special function
            if self.postpath[2]=='.all':
                res = self.env.catalog.getResourceList(self.package_id,
                                                       self.resourcetype_id)
                # XXX: r[0] not clean r.id would be better
                resource_ids = [r[0] for r in res]
                # generate corrent base path
                base = '/'+'/'.join(self.postpath[:-1])
                return self.renderResourceList(base=base, 
                                               resource=resource_ids)
        raise RequestError(http.NOT_FOUND)
    
    def _processResource(self):
        """
        Direct access on a resource consists always of a package_id, 
        resourcetype_id and an integer as document_id.
        """
        if self.method=='GET':
            return self._getResource()
        if self.method=='POST':
            return self._modifyResource()
        elif self.method=='DELETE':
            return self._deleteResource()
        raise RequestError(http.NOT_ALLOWED)
    
    def _processMapping(self):
        pass
    
    def _processAlias(self):
        """Generates a list of resources from an alias query."""
        # fetch list of uris via catalog
        aliases = self.env.registry.aliases.get(self.package_id, 
                                                self.resourcetype_id,
                                                self.postpath[-1:][0])
        try:
            uris = self.env.catalog.query(aliases[0].expr)
        except Exception, e:
            self.env.log.error(e)
            return
        # generate corrent base path
        base = '/'+'/'.join(self.postpath[:-1])
        return self.renderResourceList(base=base, resource=uris)
    
    def _getResource(self):
        """Handles a GET request on a direct resource."""
        try:
            result = self.env.catalog.getResource(self.postpath[2]).getData()
        except Exception, e:
            self.env.log.error(e)
            raise RequestError(http.NOT_FOUND)
        return result
    
    def _modifyResource(self):
        """Handles a POST request on a direct resource."""
        try:
            self.env.catalog.modifyResource(self.package_id,
                                            self.resourcetype_id,
                                            self.postpath[2],
                                            self.content)
        except Exception, e:
            self.env.log.error(e)
            raise RequestError(http.NOT_ALLOWED)
        
        # XXX: Return OK
        raise RequestError(http.NOT_ALLOWED)
    
    def _addResource(self):
        """Handles a PUT request on a direct resource."""
        try:
            res = self.env.catalog.newXmlResource(self.package_id,
                                                  self.resourcetype_id,
                                                  self.content)
        except Exception, e:
            self.env.log.error(e)
            return
        # XXX: res ID should be returned in a standardized way
        return res
    
    def _deleteResource(self):
        """Handles a DELETE request on a direct resource."""
        try:
            self.env.catalog.deleteResource(self.package_id,
                                            self.resourcetype_id,
                                            self.postpath[2])
        except Exception, e:
            self.env.log.error(e)
            return
    
    def renderResource(self, data):
        """
        Resource handler. Returns a content of this resource as string.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this document.
        """
        return data
    
    def renderResourceList(self, **kwargs):
        """
        Resource list handler. Here we return a dict of objects. Each object
        contains a list of string, e.g. {'package':['quakeml','seishub']}.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this resource list. 
        """
        return kwargs