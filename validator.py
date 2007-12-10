# -*- coding: utf-8 -*-

from seishub.util.libxmlwrapper import XmlTreeDoc, XmlSchema

class Validator(object):
    def __init__(self,value):
        self.value=value
    
    def isString(self):
        return isinstance(self.value,basestring)

class XmlSchemaValidator(Validator):
    """Class for validating xml documents against a given xml schema"""
    def __init__(self,schema,data):
        self.data=XmlTreeDoc(data)
        self.xmlschema = XmlSchema(schema)
    
    def validate(self):
        return self.xmlschema.validate(self.data)