# -*- coding: utf-8 -*-
import time

from zope.interface import implements, Interface, directlyProvides, \
                           implementedBy, Attribute
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select, Text, and_
from sqlalchemy.exceptions import IntegrityError
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
    _id = Attribute("Unique id of Serializable object.")
        

class IRelation(Interface):
    """marker interface for Relation class"""


class ILazyAttribute(Interface):
    """marker interface for LazyAttribute class"""


class IDbObjectProxy(Interface):
    """marker interface for DbObjectProxy class"""


class IDbAttributeProxy(Interface):
    """marker interface for DbAttributeProxy class"""
    

class DB_NULL(object):
    """Pass this object to pickup(...) or drop(...) as a parameter value to 
    explicitly claim that parameter to be None.
    """
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
    
    db = property(getDb, setDb, "Database engine")

class DbStorage(DbEnabled):
    """Mixin providing object serialization to a sqlalchemy SQL database.
            
    Internal integer ids are stored into the _id attribute of Serializable 
    objects.
    """
    def __init__(self, db, debug = False):
        DbEnabled.__init__(self, db)
        self.debug = debug
    
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
                                      (type(value), str(value)))
                    value = value._id
                col = col.name
#                kwargs = self._to_kwargs(value)
#                value = self.pickup(col, **kwargs)._id
            elif ILazyAttribute.providedBy(col):
                col = col.name
            # convert None to '' on Text columns
            if value is None:
                if isinstance(table.c[col].type, Text):
                    value = ''
                else:
                    continue
            d[col] = value
        return d
    
    def _where_clause(self, table, map, values):
        cl = ClauseList(operator = "AND")
        for key, val in values.iteritems():
            if key not in map.keys():
                continue
            if val is None:
                continue
            col = map[key]
            if IRelation.providedBy(col):
                if isinstance(val, dict):
                    # read related object included in the query
                    try:
                        o = self.pickup(col.cls, **val)
                        assert len(o) == 1 # sanity check
                        val = o[0]._id
                    except IndexError:
                        raise DbError('A related object could not be '+\
                                      'located in the database. %s: %s' %\
                                      (col.cls, str(val)))
                elif isinstance(val, col.cls): 
                    # related object was included, use it's id 
                    val = val._id
                elif val == DB_NULL:
                    val = None
                elif val:
                    raise DbError("Invalid value for key '%s': %s" %\
                                  (str(col.name), str(val)))
                col = col.name
#            if val == None and isinstance(table.c[col].type, Text):
#                val = ''
            cl.append(table.c[col] == val)
        return cl
    
    def _generate_query(self, q, table, mapping, params, joins = None, 
                        order_by = dict()):
        params = params or dict()
        for attr, col in mapping.iteritems():
            value = params.get(attr, None)
            if IRelation.providedBy(col):
                colname = col.name
            else:
                colname = col
            if IRelation.providedBy(col) and value is not DB_NULL: # Object relation
                if col.lazy and not value and attr not in order_by.keys(): 
                    # skip lazy relations, if not needed for a where clause
                    continue
                if isinstance(value, col.cls) and hasattr(value, '_id'): 
                    # if there is an object of correct type included with the 
                    # query, providing an id, use that id instead
                    # TODO: instead of using the id it would be more common to
                    # use any parameters provided by the object
                    value = {'_id':value._id}
                rel_tab = col.cls.db_table
                # from here on value should be none or a dict, 
                # or something went wrong
                assert not value or isinstance(value, dict)
                if col.lazy and value and '_id' in value.keys() \
                    and attr not in order_by.keys():
                    # in this case we got the id for the related object somehow
                    # but don't need the related object, as it's non-eagerly 
                    # loaded and not part of the ORDER_BY clause
                    q = q.where(table.c[colname] == value['_id'])
                else:
                    # related object is eagerly loaded or needed for the query
                    if not joins:
                        joins = table.outerjoin(rel_tab, onclause = 
                                                (table.c[colname] == rel_tab.c['id']))
                    else:
                        joins = joins.outerjoin(rel_tab, onclause = 
                                                (table.c[colname] == rel_tab.c['id']))
                    rel_order_by = order_by.get(attr, dict())
                    q, joins = self._generate_query(q, rel_tab, 
                                                    col.cls.db_mapping, value, 
                                                    joins, rel_order_by)
            elif value == DB_NULL:
                q = q.where(table.c[colname] == None)
            elif value:
                q = q.where(table.c[colname] == value)
            # don't read lazy attribute columns
            if not ILazyAttribute.providedBy(col):
                q.append_column(table.c[colname])
        return q, joins
    
    def _generate_obj(self, cls, result):
        obj = cls()
        table = cls.db_table
        for attr, col in cls.db_mapping.iteritems():
            if IRelation.providedBy(col): # object relation
                if col.lazy:
                    rel_id = result[str(table) + '_' + col.name]
                    value = col.cls()
                    if rel_id:
                        value = DbObjectProxy(self, col.cls, _id = rel_id)
                else:
                    value = self._generate_obj(col.cls, result)
            elif ILazyAttribute.providedBy(col): # lazy attribute
                value = DbAttributeProxy(self, col, table, 
                                         {'id':result[str(table) + '_id']})
            else:
                value = result[str(table) + '_' + col]
            obj.__setattr__(attr, value)
        return obj
    
    def _get_children(self, obj):
        objs = list()
        for attr, col in obj.db_mapping.iteritems():
            if IRelation.providedBy(col):
                value = obj.__getattribute__(attr)
                if value:
                    objs.extend(self._get_children(value))
        objs.append(obj)
        return objs

    def _order_by(self, q, table, mapping, order_by = dict()):
        for col, direction in order_by.iteritems():
#             tables in ORDER BY clause also have to be in FROM clause
#            q.outerjoin(table)
            if isinstance(direction, dict):
                q = self._order_by(q, mapping[col].cls.db_table, 
                                   mapping[col].cls.db_mapping, direction)
                continue
            if direction.lower() == 'asc':
                q = q.order_by(table.c[col].asc())
            else:
                q = q.order_by(table.c[col].desc())
        return q
    
    def _to_list(self, l):
        if l is None:
            return list()
        return l
    
    def to_sql_like(self, expr):
        return expr.replace('*', '%')
        
    def store(self, *objs, **kwargs):
        """store a (list of) Serializable object(s) into specified db table  
        if objs is a list, all objects in list will be stored within the same 
        transaction.
        
        @keyword cascading: If True, also underlying related objects are 
                            stored, default is False.
        @type cascading:    bool
        """
        if hasattr(self,'debug') and self.debug:
            start = time.time()
        cascading = kwargs.get('cascading', False)
        if cascading:
            casc_objs = list()
            for o in objs:
                casc_objs.extend(self._get_children(o))
            objs = casc_objs
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        try:
            for o in objs: 
                if not ISerializable.providedBy(o):
                    raise DoesNotImplement(ISerializable)
                table = o.db_table
                kwargs = self._to_kwargs(o)
                r = conn.execute(table.insert(), **kwargs)
                o._id = r.last_inserted_ids()[0]
                
            txn.commit()
        except IntegrityError, e:
            txn.rollback()
            raise DbError(e)
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Stored %i objects in %s seconds." %\
                  (len(objs), time.time()-start)
        return True

    def pickup(self, cls, **keys):
        """Read Serializable objects with given keys from database.
        @param cls: Object type to be retrieved.
        @param **keys: kwarg list of the form: 
            - attribute_name = value
        or for relational attributes:
            - attribute_name = Object
            - attribute_name = {'attribute_name' : 'value'}
        Use DB_NULL as value to force a column to be None, 
        attribute_name = None will be ignored.
        """
        if hasattr(self,'debug') and self.debug:
            start = time.time()
        if not ISerializable.implementedBy(cls):
            raise DoesNotImplement(ISerializable)
        order_by = keys.get('_order_by', dict())
        table = cls.db_table
        map = cls.db_mapping
        db = self.getDb()
        # generate query
        q = table.select(use_labels = True)
        q, joins = self._generate_query(q, table, map, keys, 
                                        order_by = order_by)
        if joins:
            q = q.select_from(joins)
        q = self._order_by(q, table, map, order_by)
        # execute query
        r = db.execute(q)
        try:
            results = r.fetchall()
        finally:
            r.close()
        # create objects from results
        objs = list()
        for res in results:
            obj = self._generate_obj(cls, res)
            objs.append(obj)
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Loaded %i object(-tree)s in %s seconds." %\
                  (len(objs), time.time()-start)
        return self._to_list(objs)
    
    def drop(self, cls, **keys):
        """Delete object with given keys from database.
        
        @param cls: Object type to be removed.
        @param **keys: kwarg list of the form: 
            - attribute_name = value
        or for relational attributes:
            - attribute_name = Object
            - attribute_name = {'attribute_name' : 'value'}
        Use DB_NULL as value to force a column to be None, 
        attribute_name = None will be ignored.
        """
        if hasattr(self,'debug') and self.debug:
            start = time.time()
        table = cls.db_table
        map = cls.db_mapping
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        try:
            w = self._where_clause(table, map, keys)
            # cascading deletes
            for rel in map.values():
                if IRelation.providedBy(rel) and rel.cascading_delete:
                    q = select([table.c[rel.name]], w)
                    res = conn.execute(q).fetchall()
                    ids = [r[rel.name] for r in res]
                    for id in ids:
                        self.drop(rel.cls, _id = id)
            # delete parent
            conn.execute(table.delete(w))
            txn.commit()
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Deletion completed in %s seconds." %\
                  (time.time()-start)
        return True


class Serializable(object):
    """Subclasses may be serialized into a DbStorage.
    
    Serializable objects should implement serializable attributes via the
    db_property descriptor.
    All arguments of the __init__ method of a Serializable object have to be 
    optional and should default to None!
    """
    
    implements(ISerializable)
    
    db_mapping = dict()
    
    def __init__(self, *args, **kwargs):
        # TODO: remove?
        self._id = None
        
    def _getId(self):
        try:
            return self._serializable_id
        except:
            return None
        
    def _setId(self, id):
        if id and not (isinstance(id, int) or isinstance(id, long)):
            raise TypeError("Id has to be integer or long. Got a %s." %\
                            str(type(id)))
        self._serializable_id = id
        
    _id = property(_getId, _setId, 'Internal id (integer)')
    

class DbObjectProxy(object):
    implements(IDbObjectProxy)
    
    def __init__(self, db_storage, cls, **kwargs):
        self.db_storage = db_storage
        self.cls = cls
        self.kwargs = kwargs
        directlyProvides(self, list(implementedBy(cls)))
        
    def get(self):
        try:
            return self.db_storage.pickup(self.cls, **self.kwargs)[0]
        except IndexError:
            raise DbError('A related object could not be located in '+\
                          'the database. %s: %s' % (self.cls, self.kwargs))
            

class DbAttributeProxy(object):
    """@param attr: LazyAttribute instance
    @param table: table containing attribute and keys
    @param keyargs: attribute dict uniquely identifying the object
    """
    implements(IDbAttributeProxy)
    
    def __init__(self, db_storage, attr, table, keyargs):
        self.db_storage = db_storage
        self.attr_name = attr.name
        self.table = table
        self.keyargs = keyargs
        
    def get(self):
        w = ClauseList()
        for k in self.keyargs.keys():
            w.append(self.table.c[k] == self.keyargs[k])
        try:
            q = select([self.table.c[self.attr_name]], w)
            res = self.db_storage.db.execute(q).fetchall()
            assert len(res) <= 1 # sanity check
            return res[0][self.attr_name]
        except IndexError:
            raise DbError('An error occurred while getting related object ' +\
                          'data "%s": %s' % (self.attr_name, self.keyargs))


class db_property(property):
    """Use this property instead of the python 'property' descriptor to support 
    lazy object getting.
    Usage is like standard 'property' descriptor with an additional parameter:
    @param attr: name of the attribute used by the property 
    """
    
    def __init__(self, *args, **kwargs):
        self.attr = kwargs.pop('attr', None)
        property.__init__(self, *args, **kwargs)
    
    def __get__(self, obj, objtype):
        if not self.attr:
            return property.__get__(self, obj, objtype)
        data = obj.__getattribute__(self.attr)
        if IDbObjectProxy.providedBy(data) or \
           IDbAttributeProxy.providedBy(data):
            obj.__setattr__(self.attr, data.get())
        return property.__get__(self, obj, objtype)
    
    def __set__(self, obj, value):
        if IDbAttributeProxy.providedBy(value):
            obj.__setattr__(self.attr, value)
            return
        return property.__set__(self, obj, value)
            

class Relation(object):
    """Defines a one-to-one/many-to-one relation between Serializable objects.
    
    @param cls: class of target object type
    @param name: name of the referencing column in database table
    @param lazy: lazy getting of related objects (True by default), in order to
    support lazy getting, usage of the 'db_property' descriptor is mandatory.
    @param cascading_delete: automatically delete related objects, when parent
    is deleted (False by default)"""
    
    implements(IRelation)
    
    def __init__(self, cls, name, lazy = True, cascading_delete = False):
        self.cls = cls
        self.name = name
        self.lazy = lazy
        # TODO: not implemented yet
        self.cascading_delete = cascading_delete
        

class LazyAttribute(object):
    """Defines a lazy object attribute.
    Loads a propertie's data not until attribute is accessed for the first 
    time.
    
    @param name: name of the database column holding attribute data 
    """

    implements(ILazyAttribute)
    
    def __init__(self, name):
        self.name = name
