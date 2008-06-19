# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select #@UnresolvedImport 
from sqlalchemy.sql import and_ #@UnresolvedImport 
from sqlalchemy.sql.expression import ClauseList #@UnresolvedImport 

from seishub.db.util import DbStorage
from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.errors import AddResourceError, GetResourceError, \
                                 DeleteResourceError
from seishub.xmldb.xmlresource import XmlResource, ResourceInformation
from seishub.xmldb.defaults import resource_tab, resource_meta_tab 

class XmlDbManager(DbStorage):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    db_tables = {XmlResource: resource_tab, 
                 ResourceInformation: resource_meta_tab}
    
    db_mapping = {XmlResource:
                      {'uid':'id',
                       'data':'data'},
                  ResourceInformation:
                      {'id':'res_id',
                       'package_id':'package_id',
                       'resourcetype_id':'resourcetype_id',
                       'revision':'revision'}
                  }

    # methods from IResourceStorage            
    def addResource(self, xml_resource):
        """Add a new resource to the storage
        @return: True on success"""
        if (not xml_resource.data) or len(xml_resource.data) == 0:
            raise AddResourceError('Empty document!')
        try:
            self.store(xml_resource, xml_resource.info)
        except Exception, e:
            raise AddResourceError(e)
        return True
    
    def getResource(self, uid):
        """Get a resource by it's id from the database.
        @return: XmlResource or None
        """
        # XXX: bypass xml parsing on resource retrieval
        try:
            xml_resource = self.pickup(XmlResource, uid = uid)
            xml_resource.info = self.pickup(ResourceInformation, id = uid)
        except Exception, e:
            raise GetResourceError("No resource with id %s" % uid, e)
        return xml_resource
    
    def deleteResource(self, uid):
        """Remove a resource from the storage.
        @return: True on success
        """
        try:
            long(uid)
        except:
            raise DeleteResourceError("Invalid uid: %s" % uid)
        try:
            self.drop(ResourceInformation, id = uid)
            self.drop(XmlResource, uid = uid)
        except Exception, e:
            raise DeleteResourceError("Error deleting resource", e)      
        return True
    
    def getResourceList(self, package_id = None, resourcetype_id = None):
        # XXX: return dictionary
        w = ClauseList(operator = "AND")
        if package_id:
            w.append(resource_meta_tab.c.package_id == package_id)
        if resourcetype_id:
            w.append(resource_meta_tab.c.resourcetype_id == resourcetype_id)
        query = select([resource_meta_tab.c.res_id,
                        resource_meta_tab.c.package_id,
                        resource_meta_tab.c.resourcetype_id], 
                        w)
        try:
            res = self._db.execute(query)
            reslist = res.fetchall()
        except:
            return list()
        finally:
            res.close()
        return [ResourceInformation(res['res_id'], 
                                    res['package_id'], 
                                    res['resourcetype_id']) for res in reslist]
    
    def getUriList(self,package_id = None, resourcetype_id = None):
        # XXX: to be removed
        res = self.getResourceList(package_id, resourcetype_id)
        return ['/'+r[1]+'/'+r[2]+'/'+str(r[0]) for r in res]

    def resourceExists(self, package_id, resourcetype_id, uid):
        # XXX: package_id and resourcetypeid senseless here?
        query = select([resource_meta_tab.c.res_id],
                       and_(resource_meta_tab.c.package_id == package_id,
                            resource_meta_tab.c.resourcetype_id == resourcetype_id,
                            resource_meta_tab.c.res_id == uid))
        try:
            res = self._db.execute(query)
            res.fetchall()[0]
        except:
            return False
        finally:
            res.close()
        return True
