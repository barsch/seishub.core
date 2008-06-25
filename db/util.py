# -*- coding: utf-8 -*-
from zope.interface import implements, Interface
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select #@UnresolvedImport
from sqlalchemy.sql.expression import ClauseList #@UnresolvedImport


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


class DbEnabled(object):
    """Mixin providing access to a sqlite database manager"""
    implements(IDbEnabled)
    
    def __init__(self, db):
        self.setDb(db.engine)

    def setDb(self, db):
        self._db = db
        
    def getDb(self):
        return self._db


class DbStorage(DbEnabled):
    """Mixin providing object serialization to a sqlite SQL database.
    db_tables and db_mapping must be defined by subclasses.
    where db_tables is of the form: 
            {Class1:table1, 
             Class2:table2, 
             ... }
    db_mapping should look like: 
            {Class1:{'property1':'column1',
                     'property2':'column2',
                     ...}, 
             Class2:{'property1':'column1',
                     'property2':'column2',
                     ...}
            }
    """
    
    db_tables = dict()
    db_mapping = dict()
    
    def _to_kwargs(self, table, o, map):
        d = dict()
        for field in map:
            value = o.__getattribute__(field)
            if value is None:
                continue
            if isinstance(value, unicode):
                value = value.encode("utf-8")
#            if not isinstance(value, bool) or isinstance(value, unicode):
#                value = str(value)
            d[map[field]] = value
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
    
    def _to_order_by(self, table, order_by = dict()):
        cl = ClauseList()
        for ob in order_by:
            cl.append(table.c[ob].desc())
        return cl
    
    def _to_list(self, l):
        if l is None:
            return list()
        return l
    
    def to_sql_like(self, expr):
        return expr.replace('*', '%')
        
    def store(self, *objs):
        """store a (list of) Serializable object(s) into specified db table  
        if objs is a list, all objects in list will be stored within the same 
        transaction"""
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()

        try:
            for o in objs: 
                if not ISerializable.providedBy(o):
                    raise DoesNotImplement(ISerializable)
                cls = o.__class__
                table = self.db_tables[cls]
                map = self.db_mapping[cls]
                kwargs = self._to_kwargs(table, o, map)
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
        null = keys.get('_null', list())
        order_by = keys.get('_order_by', list())
        table = self.db_tables[cls]
        map = self.db_mapping[cls]
        db = self.getDb()
        c = list()
        for col in map.values():
            c.append(table.c[col])
        w = self._to_where_clause(table, map, keys, null)
        ob = self._to_order_by(table, order_by)
        q = select(c, w, order_by = ob)
        r = db.execute(q)
        try:
            results = r.fetchall()
        finally:
            r.close()
        objs = list()
        for res in results:
            obj = cls()
            for field in map:
                obj.__setattr__(field, res[map[field]])
            objs.append(obj)
                    
        return self._to_list(objs)
    
    def drop(self, cls, **keys):
        """delete object with given keys from database"""
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        table = self.db_tables[cls]
        try:
            map = self.db_mapping[cls]
            w = self._to_where_clause(table, map, keys)
#            if len(w) == 0:
#                continue
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
    Serializable objects should implement serializable attributes via the
    python property descriptor"""
    
    implements(ISerializable)
    
    def __init__(self, *args, **kwargs):
        super(Serializable, self).__init__(*args, **kwargs)
        self.__id = None
        
    def _getId(self):
        return self.__id
    
    def _setId(self, id):
        self.__id = id
        
    _id = property(_getId, _setId, 'Internal id')
