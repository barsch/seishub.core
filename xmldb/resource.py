# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.db.util import Serializable, Relation
from seishub.util.xml import IXmlDoc, XmlTreeDoc
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper
from seishub.xmldb.defaults import resource_meta_tab, resource_tab
from seishub.xmldb.errors import XmlResourceError
from seishub.xmldb.interfaces import IResource, IResourceInformation,\
                                     IXmlResource
from seishub.xmldb.package import PackageSpecific

class Resource(Serializable):
    """Resource base class"""
    implements(IResource)
    
    def __init__(self, data = None, info = None):
        self.data = data
        self.info = info
        Serializable.__init__(self)
            
    def getData(self):
        return self.__data
    
    def setData(self, newdata):
        self.__data = newdata
    
    data = property(getData, setData, 'Raw data')
    
    def _getResource_Id(self):
        return self._id
    
    def _setResource_Id(self,id):
        self._id = id
    
    resource_id = property(_getResource_Id, _setResource_Id, 'unique id')
    
    def getInfo(self):
        try:
            return self._info
        except:
            return None
    
    def setInfo(self, data):
        if not IResourceInformation.providedBy(data):
            raise TypeError("%s is not a ResourceInformation" % str(data))
        self._info = data
        self._info.resource = self
    
    info = property(getInfo, setInfo, 'resource information')
    

class XmlResource(Resource):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    
    implements (IXmlResource)
    
    db_table = resource_tab
    db_mapping = {'resource_id':'id',
                  'data':'data',
                  '_id':'id'
                  }
    
    def __init__(self, package = PackageWrapper(), 
                 resourcetype = ResourceTypeWrapper(), data = None,
                 id = None, version_control = False):
        self.__xml_doc = None
        info = ResourceInformation(package, resourcetype, id,
                                   version_control = version_control)
        Resource.__init__(self, data, info)
        
#    # auto update resource id when Serializable id is changed:
#    def _setId(self, id):
#        Serializable._setId(self, id)
#        self.resource_id = id
    
    # pass ResourceInformation.id to XmlResource.id for easy access (read-only)
    def getId(self):
        return self.info.id
    
    id = property(getId, "Integer identification number (external id)")
    
    # overloaded method setData from Resource
    # gets invoked by Resource's constructor
    def setData(self, xml_data):
        # parse and validate xml_data
        # decode raw data to utf-8 unicode string
        if xml_data is None or len(xml_data) == 0:
            return Resource.setData(self, xml_data)
            #raise XmlResourceError("No xml data given")
        xml_data = str(xml_data)
        if not isinstance(xml_data, unicode) and xml_data:
            xml_data = unicode(xml_data, "utf-8")
            
        try:
            self.__xml_doc = self._validateXml_data(xml_data)
        except Exception, e:
            raise XmlResourceError(e)
        
        return Resource.setData(self, xml_data)
    
    def getData(self):
        data = super(XmlResource,self).getData()
        if not data:
            return None
        # XXX: use encoded byte strings or unicode strings internally?
        return data.encode("utf-8")
        #return data
    
    data = property(getData, setData, 'Raw xml data as a string')
    
    
    def getXml_doc(self):
        return self.__xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise TypeError("%s is not an IXmlDoc" % str(xml_doc))
        else:
            self.__xml_doc = xml_doc

            
#    def getUri(self):
##         XXX: remove this method or handle non existing self._id properly
#        return '/' + self.info.package_id + '/' + self.info.resourcetype_id + '/' +\
#               str(self._id)
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        #import pdb; pdb.set_trace()
        # encode before handing it to parser:
        xml_data = xml_data.encode("utf-8")
        return XmlTreeDoc(xml_data=xml_data, blocking=True)


class ResourceInformation(Serializable, PackageSpecific):
    
    implements(IResourceInformation)
    
    db_table = resource_meta_tab
    db_mapping = {'id':'id',  # external id
                  'revision':'revision',
                  'resource':Relation(XmlResource, 'resource_id'),
                  'package':Relation(PackageWrapper,'package_id'),
                  'resourcetype':Relation(ResourceTypeWrapper,
                                             'resourcetype_id'),
                  'version_control':'version_control'
                  }
    
    def __init__(self, package = PackageWrapper(), 
                 resourcetype = ResourceTypeWrapper(), id = None, 
                 revision = None, resource = None, version_control = False):
        self.version_control = version_control
        self.id = id
        self.revision = revision
        self.resource = resource
        self.package = package
        self.resourcetype = resourcetype
        
    def __str__(self):
        return '/' + self.package.package_id + '/' +\
               self.resourcetype.resourcetype_id + '/' + str(self.id)
    
    # auto update id when _Serializable__id is changed:
    def _setId(self, id):
        Serializable._setId(self, id)
        self.id = id
    
    #methods and attributes from IResourceInformation
    def getResource(self):
        return self._resource
    
    def setResource(self, data):
        self._resource = data
        if self._resource and not self._resource.info == self:
            self._resource.info = self
    
    resource = property(getResource, setResource, "related document")
    
    def getRevision(self):
        return self._revision
    
    def setRevision(self, data):
        if not self.version_control:
            self._revision = 1
        else:
            self._revision = data
         
    revision = property(getRevision, setRevision, "revision")
    
    def getId(self):
        return self._id
    
    def setId(self, data):
        self._id = data
        
    id = property(getId, setId, "Integer identification number (external id)")
