# -*- coding: utf-8 -*-
from zope.interface import implements, Interface
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select, text, Text #@UnresolvedImport
from sqlalchemy.sql.expression import ClauseList #@UnresolvedImport

class DbError(Exception):
    pass

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
        

class IRelation(Interface):
    pass


class DbEnabled(object):
    """Mixin providing access to a sqlalchemy database manager"""
    
    implements(IDbEnabled)
    
    def __init__(self, db):
        self.setDb(db.engine)

    def setDb(self, db):
        self._db = db
        
    def getDb(self):
        return self._db

class DbStorage(DbEnabled):
    """Mixin providing object serialization to a sqlalchemy SQL database.
            
    Internal integer ids are stored into the _id attribute of Serializable 
    objects.
    """
    
    def _is_sqlite(self):
        return str(self._db.url).startswith('sqlite')
    
    def _to_kwargs(self, o):
        d = dict()
        cls = o.__class__
        table = o.db_table
        for field, col in o.db_mapping.iteritems():
            value = o.__getattribute__(field)
            # object relation
            if IRelation.providedBy(col):
                if value:
                    assert isinstance(value, col.cls)
                    if not value._id:
                        raise DbError('A related object could not be '+\
                                      'located in the database. %s: %s' %\
                                      (type(value),str(value)))
                    value = value._id
                col = col.name
#                kwargs = self._to_kwargs(value)
#                value = self.pickup(col, **kwargs)._id
            # convert None to '' on Text columns
            if value is None:
                if isinstance(table.c[col].type, Text):
                    value = ''
                else:
                    continue
            # convert to byte strings
            if isinstance(value, unicode):
                value = value.encode("utf-8")
            d[col] = value
        return d
    
    def _to_where_clause(self, table, map, values, null = list()):
        cl = ClauseList(operator = "AND")
        for key, val in values.iteritems():
            if key not in map.keys():
                continue
            col = map[key]
            if IRelation.providedBy(col):
                if isinstance(val, dict): # retrieve sub-object
                    try:
                        # TODO: do this via inline selects rather than getting
                        # objects recursively
                        o = self.pickup(col.cls, **val)[0]
                        val = o._id
                        values[key] = o
                    except IndexError:
                        raise DbError('A related object could not be '+\
                                      'located in the database. %s: %s' %\
                                      (col.cls, str(val)))
                elif isinstance(val, col.cls): # object already there
                    values[key] = val
                    val = val._id
                elif val:
                    raise DbError("Invalid value for key '%s': %s" %\
                                  (str(col.name), str(val)))
                col = col.name
            if val == None:
                if key not in null:
                    continue
                elif isinstance(table.c[col].type, Text):
                    val = ''
            cl.append(table.c[col] == val)
        return cl, values
    
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
                table = o.db_table
                kwargs = self._to_kwargs(o)
                r = conn.execute(table.insert(),
                                 **kwargs)
                o._id = r.last_inserted_ids()[0]
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
        table = cls.db_table
        map = cls.db_mapping
        db = self.getDb()
        c = list()
        for col in map.values():
            if IRelation.providedBy(col):
                col = col.name
            c.append(table.c[col])
        w, keys = self._to_where_clause(table, map, keys, null)
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
            for field, col in map.iteritems():
                if IRelation.providedBy(col): # object relation
                    if field in keys and keys[field]:  
                        # use the object already retrieved during the query
                        # this avoids getting objects twice
                        assert isinstance(keys[field], col.cls)
                        val = keys[field]
                    elif res[col.name]:
                        try:
                            val = self.pickup(col.cls, _id = res[col.name])[0]
                        except IndexError:
                            raise DbError('A related object could not be '+\
                                          'located in the database. %s: %s' %\
                                          (col.cls, str(res[col.name])))
                    else:
                        # TODO: really needed ?
                        val = col.cls()
                else:
                    val = res[col]
                if val == '':
                    val = None
                obj.__setattr__(field, val)
            objs.append(obj)
                    
        return self._to_list(objs)
    
    def drop(self, cls, **keys):
        """delete object with given keys from database"""
        null = keys.get('_null', list())
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        table = cls.db_table
        try:
            map = cls.db_mapping
            w, _ = self._to_where_clause(table, map, keys, null)          
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
    
    db_mapping = dict()
    
    def __init__(self, *args, **kwargs):
        #super(Serializable, self).__init__(*args, **kwargs)
        
        # TODO: remove?
        self._id = None
        
    def _getId(self):
        try:
            return self._serializable_id
        except:
            return None
        
    def _setId(self, id):
        self._serializable_id = id
        
    _id = property(_getId, _setId, 'Internal id (integer)')
    

class Relation(object):
    implements(IRelation)
    def __init__(self, cls, name):
        self.cls = cls
        self.name = name
