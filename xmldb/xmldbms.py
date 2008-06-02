# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import ClauseList

from seishub.db.util import DbStorage
from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.xmlresource import XmlResource, ResourceInformation
from seishub.xmldb.errors import AddResourceError, GetResourceError, \
                                 DeleteResourceError
from seishub.xmldb.defaults import resource_tab, resource_meta_tab

class XmlDbManager(DbStorage):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    # XXX: order of tables is IMPORTANT here!
    db_tables = [resource_tab, resource_meta_tab]
    
    # overloaded methods from DbStorage
    def getMapping(self, table):
        if table == resource_tab:
            return {'uid':'id',
                    'data':'data'}
        if table == resource_meta_tab:
            return {'res_uid':'res_id',
                    'package_id':'package_id',
                    'resourcetype_id':'resourcetype_id',
                    'revision':'revision'}
    
    # methods from IResourceStorage            
    def addResource(self, xml_resource):
        """Add a new resource to the storage
        @return: True on success"""
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
            xml_resource.info = self.pickup(ResourceInformation, res_uid = uid)
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
            self.drop(res_uid = uid)
            self.drop(uid = uid)
        except Exception, e:
            raise DeleteResourceError("Error deleting resource", e)      
        return True
    
    def getResourceList(self, package_id = None, resourcetype_id = None):
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
        return [res.values() for res in reslist]
    
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
