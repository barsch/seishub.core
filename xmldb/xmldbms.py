# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select #@UnresolvedImport 
from sqlalchemy.sql import and_, text #@UnresolvedImport

from seishub.db.util import DbStorage
from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.errors import AddResourceError, GetResourceError, \
                                 DeleteResourceError, ResourceDeletedError
from seishub.xmldb.resource import XmlResource, ResourceInformation
from seishub.xmldb.defaults import resource_tab, resource_meta_tab, \
                                   DEFAULT_PREFIX, RESOURCE_META_TABLE

class XmlDbManager(DbStorage):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    # methods from IResourceStorage            
    def addResource(self, xml_resource):
        """Add a new resource to the storage
        @return: True on success"""
        if (not xml_resource.data) or len(xml_resource.data) == 0:
            raise AddResourceError('Empty document!')
        
        # XXX: very ugly (and unsafe) workaround for sqlite
        if self._db.name == 'sqlite':
            rev = 1
            if xml_resource.info.version_control and xml_resource.info.id:
                res = self.getResource(xml_resource.info.package,
                                       xml_resource.info.resourcetype, 
                                       xml_resource.info.id)
                rev = res.info.revision + 1
            xml_resource.info.revision = rev
        # end workaround
        
        try:
            self.store(xml_resource, xml_resource.info)
#            self.store(xml_resource.info)
        except Exception, e:
            raise AddResourceError(e)
        return True
    
    def getResource(self, package = None, resourcetype = None, id = None, 
                    revision = None, resource_id = None):
        """Get a specific resource from the database by either (package_id, 
        resourcetype_id, id, revision) or by resource_id
        @return: XmlResource or None
        """
        # XXX: bypass xml parsing on resource retrieval
        if not ((package and resourcetype and id) or resource_id):
            raise TypeError("getResource(): Invalid number of arguments.")
        info = None
        if not resource_id:
            try:
                info = self.pickup(ResourceInformation, _order_by = ['revision'], 
                                   package = package, 
                                   resourcetype = resourcetype,
                                   id = id,
                                   revision = revision)[0]
            except Exception, e:
                raise GetResourceError("Resource not found. ('%s/%s/%s/%s')" %\
                                (package.package_id, 
                                 resourcetype.resourcetype_id, id, 
                                 revision), e)
            resource_id = info.resource.resource_id
            # resource has been deleted
            if not resource_id:
                raise ResourceDeletedError("Resource has been deleted. "+\
                                           "('%s/%s/%s/%s')" %\
                                           (package.package_id, 
                                            resourcetype.resourcetype_id, 
                                            id, revision))
        if not info:
            try:
                xml_resource = self.pickup(XmlResource, 
                                           resource_id = resource_id)[0]
            except Exception, e:
                raise GetResourceError("Resource not found. ('%s')" %\
                                       (resource_id), e)
            info = self.pickup(ResourceInformation, resource = xml_resource)[0]
        return info.resource
    
    def deleteResource(self, package = None, resourcetype = None, id = None,
                       resource_id = None):
        """Remove a resource from the storage, by either (package_id, 
        resourcetype_id, id, revision) or by resource_id
        @return: True on success
        """
        if not ((package and resourcetype and id) or resource_id):
            raise TypeError("deleteResource(): Invalid number of arguments.")
        
        res = self.getResource(package, resourcetype, id, 
                               resource_id = resource_id)
        if not res.info.version_control:
            # delete resource
            try:
                self.drop(ResourceInformation, package = res.info.package,
                          resourcetype = res.info.resourcetype, 
                          id = res.info.id)
                self.drop(XmlResource, resource_id = res.resource_id)
            except Exception, e:
                raise DeleteResourceError("Error deleting resource."+\
                                          " '%s/%s/%s/%s'", e)
        else:
            # add an empty revision
            res.info.revision += 1
            res.info.resource = None
            try:
                self.store(res.info)
            except Exception, e:
                raise DeleteResourceError("Error deleting version controlled"+\
                                          " resource. '%s/%s/%s/%s'", e)
        return True
    
    def getResourceList(self, package, resourcetype = None):
        # XXX: getResource and getResourceList should return the same type of 
        # objects
        res = self.pickup(ResourceInformation, 
                          package = package, resourcetype = resourcetype)
        return res
    
    def getUriList(self,package = None, resourcetype = None):
        # XXX: to be removed
        res = self.getResourceList(package, resourcetype)
        return ['/'+r[1]+'/'+r[2]+'/'+str(r[0]) for r in res]

    def resourceExists(self, package_id, resourcetype_id, id):
        # XXX: To be removed ?
        query = select([resource_meta_tab.c.resource_id],
                       and_(resource_meta_tab.c.package_id == package_id,
                            resource_meta_tab.c.resourcetype_id == resourcetype_id,
                            resource_meta_tab.c.id == id))
        try:
            res = self._db.execute(query)
            res.fetchall()[0]
        except:
            return False
        finally:
            res.close()
        return True
