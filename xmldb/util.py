# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import ClauseList

from seishub.xmldb.interfaces import IDbEnabled, ISerializable

class DbEnabled(object):
    """Mixin providing access to a sqlite database manager"""
    implements(IDbEnabled)
    
    def __init__(self, db):
        self.setDb(db)

    def setDb(self, db):
        self._db = db.engine
        
    def getDb(self):
        return self._db
        
class DbStorage(DbEnabled):
    """Mixin providing object serialization to a sqlite SQL database"""
    
    db_tables = list()
    
    def _to_kwargs(self, fields, map):
        d = dict()
        for field in map:
            value = fields[field]
            if not value:
                continue
            d[map[field]] = value
        return d
    
    def _to_where_clause(self, table, map, values):
        cl = ClauseList(operator = "AND")
        for key in values:
            cl.append(table.c[map[key]] == values[key])
        return cl
       
    def getMapping(self, table):
        raise NotImplementedError("Implemented by subclasses")
        
    def store(self, obj):
        """store a Serializable object into database"""
        if not ISerializable.providedBy(obj):
            raise DoesNotImplement(ISerializable)
        
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        
        try:
            for table in self.db_tables:
                fields = obj.getFields()
                map = self.getMapping(table)
                kwargs = self._to_kwargs(fields, map)
                r = conn.execute(table.insert(),
                                 **kwargs)
                obj._setId(r.last_inserted_ids()[0])
            txn.commit()
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        
        return True

    def pickup(self, obj, **keys):
        """pickup Serializable object with given keys from database"""
        if not ISerializable.providedBy(obj):
            raise DoesNotImplement(ISerializable)
        
        table = self.db_tables[0]
        map = self.getMapping(table)
        db = self.getDb()
        c = list()
        for col in map.values():
            c.append(table.c[col])
        w = self._to_where_clause(table, map, keys)
        r = db.execute(select(c, w))
        try:
            res = r.fetchall()[0]
        finally:
            r.close()
        for field in map:
            obj.__setattr__(field, res[map[field]])
        return True
    
    def drop(self, **keys):
        """delete object with given keys from database"""
        # use list of tables in reverse order
        rtables = list(self.db_tables)
        rtables.reverse()
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        try:
            for table in rtables:
                map = self.getMapping(table)
                w = self._to_where_clause(table, map, keys)
                conn.execute(table.delete(w))
            txn.commit()
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        return True
    

class Serializable(object):
    """Subclasses may be serialized into a DbStorage
    Serializable objects have to overload the getFields method and should 
    implement serializable attributes via the python 'property' descriptor"""
    
    implements(ISerializable)
    
    def __init__(self, *args, **kwargs):
        super(Serializable, self).__init__(*args, **kwargs)
        self.__id = None
        
    def _getId(self):
        return self.__id
    
    def _setId(self, id):
        self.__id = id
        
    _id = property(_getId, _setId, 'Internal id')
    
    def getFields(self):
        """return a dictionary of properties to be serialized
        e.g: 
        return {'property1':property1,
                'property2':property2,
                ...}
        """
        raise NotImplementedError("Implemented by subclasses")
