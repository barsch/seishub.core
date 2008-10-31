# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy.sql import and_

from seishub.exceptions import SeisHubError, InvalidParameterError
from seishub.exceptions import NotFoundError, DeletedObjectError
from seishub.exceptions import DuplicateObjectError
from seishub.db.util import DbStorage, DbError
from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.resource import XmlDocument, Resource

class XmlDbManager(DbStorage):
    """XmlDocument layer, connects Resources to relational db storage"""
    implements(IResourceStorage)
    
    # methods from IResourceStorage            
    def addResource(self, xml_resource = Resource()):
        """Add a new resource to the storage
        @return: True on success"""
        if not xml_resource.document.data or xml_resource.document.data == "":
            raise InvalidParameterError('Empty document!')
                
        if xml_resource.resourcetype.version_control:
            xml_resource.revision = None
            
        # XXX: very ugly (and unsafe) workaround for sqlite
        #if self._db.name == 'sqlite':
        rev = 1
        if xml_resource.resourcetype.version_control and \
           (xml_resource.id or xml_resource.name):
            try:
                res = self._getResource(xml_resource.package,
                                       xml_resource.resourcetype, 
                                       xml_resource.name,
                                       id = xml_resource.id)
                rev = res.revision + 1
            except NotFoundError: # new resource -> revision = 1
                pass
        xml_resource.revision = rev
        # end workaround
        try:
            if not xml_resource.document._id:
                self.store(xml_resource.document.meta,
                           xml_resource.document, 
                           xml_resource)
            else:
                self.store(xml_resource)
        except DbError, e:
            msg = "Error adding a resource: A resource with the given " +\
                  "paramters already exists."
            raise DuplicateObjectError(msg, e)
        return True
    
    def modifyResource(self, xml_resource = Resource()):
        old = self._getResource(xml_resource.package, 
                                xml_resource.resourcetype, 
                                xml_resource.name)
        # preserve creator
        xml_resource.document.meta.uid = old.document.meta.uid
        if xml_resource.resourcetype.version_control:
            xml_resource.name = old.name
            xml_resource.id = old.id
            return self.addResource(xml_resource)
        self._deleteResource(old)
        self.addResource(xml_resource)
        
    def moveResource(self, package, resourcetype, old_name, new_name):
        # TODO: move update stuff to db.util
        table = Resource.db_table
        u = table.update(and_(table.c.package_id == package._id,
                         table.c.resourcetype_id == resourcetype._id,
                         table.c.name == old_name))
        self.db.execute(u, name = new_name)
    
    def _getResource(self, package = None, resourcetype = None, name = None, 
                     revision = None, id = None):
        # XXX: preformance? get latest revision ONLY
        try:
            res = self.pickup(Resource, _order_by = {'revision':'desc'}, 
                              package = package, 
                              resourcetype = resourcetype,
                              name = name,
                              revision = revision,
                              id = id)[0]
        except IndexError:
            raise NotFoundError("Resource not found. ('%s/%s/%s/%s')" %\
                                (package.package_id, 
                                 resourcetype.resourcetype_id, name, 
                                 revision))
        return res
    
    def getResource(self, package = None, resourcetype = None, name = None, 
                    revision = None, document_id = None, id = None):
        """Get a specific resource from the database by either (package_id, 
        resourcetype_id, name, revision) or by document_id
        @return: XmlDocument or None
        """
        # XXX: bypass xml parsing on resource retrieval
        if not ((package and resourcetype and (name or id)) or document_id):
            raise TypeError("getResource(): Invalid number of arguments.")
        if document_id:
            try:
                res = self.pickup(Resource, 
                                  document = {'_id':document_id})[0]
            except IndexError, e:
                raise NotFoundError("Resource not found. ('%s')" %\
                                    (document_id), e)
            return res
        res = self._getResource(package, resourcetype, name, revision, id)
        # resource has been deleted
        if not res.document._id:
            raise DeletedObjectError("The requested resource has been "+\
                                     "deleted. ('%s/%s/%s/%s')" %\
                                       (package.package_id, 
                                        resourcetype.resourcetype_id, 
                                        name, revision))
        return res
    
    def _deleteResource(self, res):
        try:
            self.drop(Resource, package = res.package,
                      resourcetype = res.resourcetype, 
                      _id = res._id,
                      revision = res.revision)
            # XXX: check if document is referenced elsewhere
            if res.document._id:
                self.drop(XmlDocument, _id = res.document._id)
        except Exception, e:
            raise SeisHubError("Error deleting resource. '%s/%s/%s/%s'", e)

    def deleteResource(self, package = None, resourcetype = None, name = None,
                       revision = None, document_id = None, id = None):
        """Remove a resource from the storage, by either (package_id, 
        resourcetype_id, id, revision) or by document_id
        
        Note: if (package, resourcetype, id) is given and resource
        is version controlled, a new, empty revision will be added instead of
        deleting the resource, to delete all revisions of a resource use
        deleteResources() instead.
        """
        # XXX: get resource really needed in any case?
        if not ((package and resourcetype and (name or id)) or document_id):
            raise TypeError("deleteResource(): Invalid number of arguments.")
        if document_id:
            res = self.getResource(document_id = document_id)
        else:
            res = self._getResource(package, resourcetype, name, revision, id)
        
        if not res.resourcetype.version_control or revision:
            # delete an unversioned resource or the specified revision
            self._deleteResource(res)
        else:
            # delete a versioned resource => add an empty revision
            res.revision += 1
            res.document = None
            try:
                self.store(res)
            except Exception, e:
                raise SeisHubError("Error deleting version controlled"+\
                                   " resource. '%s/%s/%s/%s'", e)
        return True
    
    def deleteResources(self, package, resourcetype, name = None):
        """delete all resources of specified package and resourcetype,
        or delete, if name is given, all revisions of the specified resource"""
        resources = self.getResourceList(package, resourcetype, name)
        self.drop(Resource, 
                  package = package,
                  resourcetype = resourcetype, 
                  name = name)
        # also delete documents:
        for res in resources:
            try:
                self.drop(XmlDocument, _id = res.document._id)
            except DbError:
                pass
            
    def revertResource(self, package, resourcetype, name, revision, id = None):
        """Add specified revision of a resource as new"""
        resource = self.getResource(package, resourcetype, name, revision, 
                                    id = id) 
        self.addResource(resource)
    
    def getResourceList(self, package, resourcetype = None, name = None,
                        id = None):
        """get a list of resources
        if package, resourcetype and name is given returns all revisions in 
        case of a version controlled resource
        """
        res = self.pickup(Resource, 
                          package = package, resourcetype = resourcetype,
                          name = name,
                          _id = id)
        return res
    
    
#    def getUriList(self,package = None, resourcetype = None):
#        # XXX: to be removed
#        res = self.getResourceList(package, resourcetype)
#        return ['/'+r[1]+'/'+r[2]+'/'+str(r[0]) for r in res]

#    def resourceExists(self, package_id, resourcetype_id, id):
#        # XXX: To be removed ?
#        query = select([resource_tab.c.resource_id],
#                       and_(resource_tab.c.package_id == package_id,
#                            resource_tab.c.resourcetype_id == resourcetype_id,
#                            resource_tab.c.id == id))
#        try:
#            res = self._db.execute(query)
#            res.fetchall()[0]
#        except:
#            return False
#        finally:
#            res.close()
#        return True
