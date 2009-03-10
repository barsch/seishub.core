# -*- coding: utf-8 -*-

from seishub.db.orm import DbStorage, DbError, DB_LIMIT
from seishub.exceptions import DuplicateObjectError, InvalidParameterError, \
    NotFoundError
from seishub.xmldb.defaults import resource_tab
from seishub.xmldb.resource import XmlDocument, Resource
from sqlalchemy import sql


class XmlDbManager(DbStorage):
    
    def _raise_not_found(self, package_id, resourcetype_id, name, id):
        if id:
            msg = "Resource with id %s not found."
            raise NotFoundError(msg % id)
        msg = "Resource not found. ('%s/%s/%s')"
        raise NotFoundError(msg % (package_id, 
                                   resourcetype_id, 
                                   name))
    
    def addResource(self, resource = Resource()):
        """
        Add a new resource to the database.
        """
        if not resource.document.data or resource.document.data == "":
            raise InvalidParameterError('Empty document!')
        try:
            self.store(resource, resource.document.meta, resource.document)
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
    
    def modifyResource(self, old_resource, resource):
        """
        Modify an existing resource.
        
        In case of a version controlled resource a new revision is created.
        XXX: new revisions are created always, whether or not the resource's 
        document has actually changed -> compare old/new document ?
        """
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
    
    def renameResource(self, resource, new_name):
        """
        Rename an existing resource.
        """
        resource.name = new_name
        try:
            self.update(resource)
        except DbError, e:
            msg = "Error renaming a resource: A resource with the given " +\
                  "parameters already exists. (%s)"
            raise DuplicateObjectError(msg % str(resource), e)
    
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
        """
        Get a specific resource from the database by either (package_id, 
        resourcetype_id, name) or by document_id
        
        @param package_id: resourcetype id
        @param: resourcetype_id: package id
        @param name: Name of the resource
        @param revision: revision of related document (if no revision is given,
            newest revision is used, to retrieve all revisions of a document  
            use getRevisions(...)
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
    
    def getRevisions(self, package_id = None, resourcetype_id = None, 
                     name = None, id = None):
        """
        Get all revisions of the specified resource by either 
        (package_id, resourcetype_id, name) or by id
        
        @param package_id: package id
        @param resourcetype_id: resourcetype id
        @param name: name of the resource
        @param id: get a resource by it's unique id
        @return: Resource object with all revisions accessible as a list
        """
        if not ((package_id and resourcetype_id and name) or id):
            raise TypeError("getRevisions: Invalid number of arguments.")
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
    
    def getAllResources(self, package_id, resourcetype_id = None):
        """
        Get a list of resources for specified package_id and resourcetype_id.
        """
        res = self.pickup(Resource, 
                          resourcetype = {'package':{'package_id':package_id}, 
                                          'resourcetype_id':resourcetype_id},
                          document = DB_LIMIT('revision', 'max'))
        return res
    
    def deleteResource(self, resource=None, resource_id=None):
        """
        Remove a resource by a specified Resource.
        
        Note: This method removes all revisions of a resource. To delete a 
        single revision use the deleteRevision method.
        """
        if resource:
            resource_id = resource.id
        return self.drop(Resource, _id = resource_id)
    
    def deleteRevision(self, resource, revision):
        """
        Delete a certain revision for a given Resource object.
        """
        document = DB_LIMIT('revision', 'fixed', revision)
        res = self.pickup(Resource,_id = resource._id, document = document)[0]
        self.drop(XmlDocument, _id = res.document._id)
    
    def deleteAllResources(self, package_id, resourcetype_id = None):
        """
        Delete all resources of specified package_id and resourcetype_id.
        """
        self.drop(Resource, 
                  resourcetype = {'package':{'package_id':package_id}, 
                                  'resourcetype_id':resourcetype_id})
    
    def revertResource(self, package_id = None, resourcetype_id = None, 
                       name = None, revision = None, id = None):
        """
        Reverts the specified revision for the given resource by removing 
        all newer revisions than the specified one.
        """
        if not (revision and\
                ((package_id and resourcetype_id and name) or id)):
            raise TypeError("revertResource: Invalid number of arguments.")
        res = self.getRevisions(package_id, resourcetype_id, name, id) 
        for doc in res.document:
            if doc.revision > revision:
                self.drop(XmlDocument, _id = doc._id)
    
    def getAllResourceNames(self, resourcetype, limit = 100, ordered = False):
        """
        Return a list of all resource names of given resource type.
        """
        # fetch all resource names for this resource type
        query = sql.select([resource_tab.c['id'], resource_tab.c['name']])
        query = query.where(
            resource_tab.c['resourcetype_id'] == resourcetype._id
        )
        if ordered:
            query = query.order_by(resource_tab.c['name'])
        if limit:
            query = query.offset(0).limit(limit)
        return self._db.execute(query).fetchall()
