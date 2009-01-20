# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy.sql import and_

from seishub.exceptions import SeisHubError, InvalidParameterError
from seishub.exceptions import NotFoundError, DeletedObjectError
from seishub.exceptions import DuplicateObjectError
from seishub.db.util import DbStorage, DbError, DB_LIMIT
from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.resource import XmlDocument, Resource

class XmlDbManager(DbStorage):
    implements(IResourceStorage)
    
    def _raise_not_found(self, package_id, resourcetype_id, name, id):
        if id:
            msg = "Resource with id %s not found."
            raise NotFoundError(msg % id)
        msg = "Resource not found. ('%s/%s/%s')"
        raise NotFoundError(msg % (package_id, 
                                   resourcetype_id, 
                                   name))
    
    # methods from IResourceStorage            
    def addResource(self, xml_resource = Resource()):
        """Add a new resource to the database."""
        if not xml_resource.document.data or xml_resource.document.data == "":
            raise InvalidParameterError('Empty document!')
        try:
            self.store(xml_resource,
                       xml_resource.document.meta,
                       xml_resource.document)
        except DbError, e:
            msg = "Error adding a resource: A resource with the given " +\
                  "parameters already exists."
            raise DuplicateObjectError(msg, e)
#            if xml_resource.resourcetype.version_control:
#                # try to add new revision
#                try:
#                    self.store(xml_resource.document.meta,
#                               xml_resource.document)
#                except DbError, e:
#                    # same revision is already there
#                    raise DuplicateObjectError(msg, e)
#            else:
#                # resource is already there and not version controlled
#                raise DuplicateObjectError(msg, e)
    
    def modifyResource(self, resource = Resource(), id = None):
        """Modify an existing resource.
        The resource is identified via it's id.
        Parameters that are subject to change are:
            - name
            - document
            - metadata
        In case of a version controlled resource a new revision is created.
        XXX: new revisions are created always, whether or not the resource's 
        document has actually changed -> compare old/new document ?
        """
        # try to use id of resource if no id was given explicitly
        id = id or resource._id
        if not id:
            msg = "Error modifying a resource: No id was given."
            raise InvalidParameterError(msg)
        old_resource = self._getResource(id = id)
                                #xml_resource.package, 
                                #xml_resource.resourcetype, 
                                #xml_resource.name)
        if not old_resource.resourcetype._id == resource.resourcetype._id:
            msg = "Error modifying a resource: Resourcetypes of old and " +\
                  "new resource do not match. %s != %s"
            raise InvalidParameterError(msg % (old_resource.resourcetype._id,
                                               resource.resourcetype._id))
        # preserve creator
        # all other document metadata may be overwritten by the new document
        resource.document.meta.uid = old_resource.document.meta.uid
        resource._id = old_resource._id
        if resource.resourcetype.version_control:
            self.update(resource, cascading = True)
        else:
            resource.document._id = old_resource.document._id
            resource.document.meta._id = old_resource.document.meta._id
            self.update(resource, resource.document, resource.document.meta)
        
    def moveResource(self, package_id, resourcetype_id, old_name, new_name):
        """Rename an existing resource."""
        res = self._getResource(package_id, resourcetype_id, name = old_name)
        res.name = new_name
        try:
            self.update(res)
        except DbError, e:
            msg = "Error renaming a resource: A resource with the given " +\
                  "parameters already exists. (%s/%s/%s)"
            raise DuplicateObjectError(msg % (package_id, resourcetype_id, 
                                              new_name), e)
        
    
    def _getResource(self, package_id = None, resourcetype_id = None, 
                     name = None, revision = None, id = None):
        if not revision:
            # no revision specified, select newest
            document = DB_LIMIT('revision', 'max')
        else:
            # select given revision
            document = DB_LIMIT('revision', 'fixed', revision)
        if name:
            name = str(name)
        try:
            res = self.pickup(Resource, resourcetype = 
                              {'package': {'package_id':package_id},
                               'resourcetype_id':resourcetype_id}, 
                              name = name, 
                              _id = id, document = document)[0]
        except IndexError:
            self._raise_not_found(package_id, resourcetype_id, name, id)
        return res
    
    def getResource(self, package_id = None, resourcetype_id = None, 
                    name = None, revision = None, document_id = None, 
                    id = None):
        """Get a specific resource from the database by either (package_id, 
        resourcetype_id, name) or by document_id
        
        @param package_id: resourcetype id
        @param: resourcetype_id: package id
        @param name: Name of the resource
        @param revision: revision of related document (if no revision is given,
            newest revision is used, to retrieve all revisions of a document  
            use getResourceHistory(...)
        @param document_id: get a resource by related document's id
        @param id: get a resource by it's unique id
        @return: Resource or None
        """
        if not ((package_id and resourcetype_id and name) or id or\
                document_id):
            raise TypeError("getResource(): Invalid number of arguments.")
        if document_id:
            try:
                res = self.pickup(Resource, 
                                  document = {'_id':document_id})[0]
            except IndexError, e:
                raise NotFoundError("Resource not found. ('%s')" %\
                                    (document_id), e)
            return res
        res = self._getResource(package_id, resourcetype_id, name, 
                                revision, id)
        return res
    
    def _deleteResource(self, res):
        try:
            # delete resource and all of its documents (cascading_delete = True
            # for Resource.document)
            self.drop(Resource, _id = res._id, resourcetype = res.resourcetype,
                      name = res.name)
        except Exception, e:
            msg = "Error deleting resource: '%s/%s/%s'"
            raise SeisHubError(msg % (res.resourcetype.package.package_id,
                                      res.resourcetype.resourcetype_id,
                                      res.name), e)

    def deleteResource(self, package_id = None, resourcetype_id = None, 
                       name = None, document_id = None, id = None):
        """Remove a resource from the storage, by either (package_id, 
        resourcetype_id, name), by document_id or by id.
        
        Note: deleteResource() removes all revisions of a resource. To delete a
        single revision use deleteRevision(...)
        """
        # XXX: get resource really needed in any case?
        if not ((package_id and resourcetype_id and name) or id or\
                 document_id):
            raise TypeError("deleteResource(): Invalid number of arguments.")
        if document_id:
            # this is needed because db.util.drop doesn't support drop via
            # a parameter of an 'one-to-many' related object
            res = self.getResource(document_id = document_id)
            id = res.id
        if id:
            return self.drop(Resource, _id = id)
        return self.drop(Resource, resourcetype = 
                         {'package':{'package_id':package_id}, 
                          'resourcetype_id':resourcetype_id}, 
                          name = str(name))
    
    def deleteRevision(self, package_id = None, resourcetype_id = None, 
                       name = None, id = None, revision = None):
        """Delete a certain revision of the specified resource"""
        if not (revision and\
                ((package_id and resourcetype_id and name) or id)):
            raise TypeError("deleteResource: Invalid number of arguments.")
        try:
            doc_id = self._getResource(package_id, resourcetype_id, name, 
                                       revision, id).document._id
        except IndexError:
            self._raise_not_found(package_id, resourcetype_id, name, id)
        self.drop(XmlDocument, _id = doc_id)
    
    def deleteResources(self, package_id, resourcetype_id):
        """delete all resources of specified package and resourcetype"""
        self.drop(Resource, resourcetype = 
                  {'package':{'package_id':package_id}, 
                   'resourcetype_id':resourcetype_id})
    
    def revertResource(self, package_id = None, resourcetype_id = None, 
                       name = None, revision = None, id = None):
        """Reverts the specified revision for the given resource by removing 
        all newer revisions than the specified one.
        """
        if not (revision and\
                ((package_id and resourcetype_id and name) or id)):
            raise TypeError("revertResource: Invalid number of arguments.")
        res = self.getResourceHistory(package_id, resourcetype_id, name, id) 
        for doc in res.document:
            if doc.revision > revision:
                self.drop(XmlDocument, _id = doc._id)
    
    def getResourceList(self, package_id, resourcetype_id = None):
        """get a list of resources for specified package and resourcetype"""
        res = self.pickup(Resource, 
                          resourcetype = {'package':{'package_id':package_id}, 
                                          'resourcetype_id':resourcetype_id},
                          document = DB_LIMIT('revision', 'max'))
        return res
    
    def getResourceHistory(self, package_id = None, resourcetype_id = None, 
                           name = None, id = None):
        """Get all revisions of the specified resource by either 
        (package_id, resourcetype_id, name) or by id
        @param package_id: package id
        @param resourcetype_id: resourcetype id
        @param name: name of the resource
        @param id: get a resource by it's unique id
        @return: Resource object with all revisions accessible as a list
        """
        if not ((package_id and resourcetype_id and name) or id):
            raise TypeError("getResourceHistory: Invalid number of arguments.")
        if name:
            name = str(name)
        try:
            res = self.pickup(Resource, 
                              _order_by = {'document':{'revision':'asc'}}, 
                              resourcetype = 
                                {'package':{'package_id':package_id}, 
                                 'resourcetype_id':resourcetype_id},
                              name = name,
                              _id = id)[0]
        except IndexError:
            self._raise_not_found(package_id, resourcetype_id, name, id)
        return res
