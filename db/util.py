# -*- coding: utf-8 -*-
from zope.interface import implements, Interface
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import ClauseList


class IDbEnabled(Interface):
    """Object provides access to db manager"""
    def setDb(db):
        """@param db: database engine"""
        
    def getDb():
        """@return: database engine"""
        
        
class ISerializable(Interface):
    """Object providing functionality for serialization"""
    def _getId():
        """return internal storage id"""
    
    def _setId(self, id):
        """set internal storage id"""
    
    def getFields():
        """@return: dict of the form {'fieldname':value}"""
        

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
            if field not in fields.keys():
                continue
            value = fields[field]
            if not value:
                continue
            d[map[field]] = str(value)
        return d
    
    def _to_where_clause(self, table, map, values, null = list()):
        cl = ClauseList(operator = "AND")
        for key in values:
            if key not in map.keys():
                continue
            if values[key] == None and key not in null:
                continue
            cl.append(table.c[map[key]] == values[key])
        return cl
    
    def _simplify_list(self, l):
        if len(l) <= 1:
            try:
                return l[0]
            except IndexError:
                return None
        return l
    
    def to_sql_like(self, expr):
        return expr.replace('*', '%')
       
    def getMapping(self, table):
        raise NotImplementedError("Implemented by subclasses")
        
    def store(self, *objs):
        """store a (list of) Serializable object(s) into database
        if obj is a list, all objects in list will be stored within the same 
        transaction"""
        obj = list(objs)
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        
        try:
            for o in obj: # store all objects within same transaction
                if not ISerializable.providedBy(o):
                    raise DoesNotImplement(ISerializable)
                
                for table in self.db_tables:
                    fields = o.getFields()
                    map = self.getMapping(table)
                    kwargs = self._to_kwargs(fields, map)
                    if len(kwargs) == 0:
                        continue
                    r = conn.execute(table.insert(),
                                     **kwargs)
                    o._setId(r.last_inserted_ids()[0])
            txn.commit()
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        
        return True

    def pickup(self, cls, **keys):
        """pickup Serializable objects with given keys from database"""
        if not ISerializable.implementedBy(cls):
            raise DoesNotImplement(ISerializable)
        cls_fields = cls().getFields()
        null = keys.get('null', list())

        for table in self.db_tables:
            map = self.getMapping(table)
            fields = [field for field in map.keys() if field in cls_fields.keys()]
            if len(fields) == 0:
                continue
            db = self.getDb()
            c = list()
            for col in map.values():
                c.append(table.c[col])
            w = self._to_where_clause(table, map, keys, null)
            r = db.execute(select(c, w))
            try:
                results = r.fetchall()
            finally:
                r.close()
            objs = list()
            for res in results:
                obj = cls()
                for field in map:
                    if field in obj.getFields():
                        obj.__setattr__(field, res[map[field]])
                objs.append(obj)
        return self._simplify_list(objs)
    
    def drop(self, **keys):
        """delete object with given keys from database"""
        # use list of tables in reverse order
        rtables = list(self.db_tables)
        #rtables.reverse()
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        try:
            for table in rtables:
                map = self.getMapping(table)
                w = self._to_where_clause(table, map, keys)
                if len(w) == 0:
                    continue
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
