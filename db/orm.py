# -*- coding: utf-8 -*-
"""
The database object-relational mapping (ORM) class.
"""

import time
from zope.interface import implements, Interface, directlyProvides, \
                           implementedBy, Attribute
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select, Text, or_, and_
from sqlalchemy.exceptions import IntegrityError, NoSuchColumnError
from sqlalchemy.sql.expression import ClauseList


class DbError(Exception):
    pass


class IDbEnabled(Interface):
    """
    Object provides access to DB manager.
    """
    def setDb(db):
        """
        @param db: database engine
        """
        
    def getDb():
        """
        @return: database engine
        """


class ISerializable(Interface):
    """
    Object providing functionality for serialization.
    """
    _id = Attribute("Unique id of Serializable object.")
        


class IRelation(Interface):
    """
    Marker interface for Relation class.
    """


class ILazyAttribute(Interface):
    """
    Marker interface for LazyAttribute class.
    """


class IDbObjectProxy(Interface):
    """
    Marker interface for DbObjectProxy class.
    """


class IDbAttributeProxy(Interface):
    """
    Marker interface for DbAttributeProxy class.
    """


class DB_NULL(object):
    """
    Pass this class to pickup(...) or drop(...) as a parameter value to 
    explicitly claim that parameter to be None.
    """
    pass


class DB_LIMIT(object):
    """
    Pass this object to pickup(...) to select only the object being 
    maximal, minimal or having a fixed value for the given attribute in a 
    x-to-many relation.
    """
    def __init__(self, attr, type = 'max', value = None):
        """
        @param attr: name of the attribute to be minimized/maximized/fixed
        @param type: 'max'|'min'|'fixed'
        @param value: if type == 'fixed', value to be taken by attribute
        """
        self.attr = attr
        self.type = type
        self.value = value
        

class DB_LIKE(object):
    """
    Pass this object to pickup(...) as a value, to select all objects where
    a parameter is LIKE the given value.
    Use '%' as wildcard.
    """
    def __init__(self, value):
        """
        @param attr: name of the attribute to be minimized/maximized/fixed
        @param type: 'max'|'min'|'fixed'
        @param value: if type == 'fixed', value to be taken by attribute
        """
        if not isinstance(value, basestring):
            raise ValueError("DB_LIKE: String expected!")
        self.value = value

class DbEnabled(object):
    """
    Mixin providing access to a sqlalchemy database manager.
    """
    implements(IDbEnabled)
    
    def __init__(self, db):
        self.setDb(db.engine)
    
    def setDb(self, db):
        self._db = db
    
    def getDb(self):
        return self._db
    
    db = property(getDb, setDb, "Database engine")


class DbStorage(DbEnabled):
    """
    Mixin providing object serialization to a sqlalchemy SQL database.
    
    Internal integer ids are stored into the _id attribute of Serializable 
    objects. Each object has an unique id for that object type.
    
    Known bugs and limitations of the DbStorage mapping tool:
        * 'many-to-many' relations are not (yet) supported
        * selecting / dropping with parameters depending on a 'to-many' 
        relation are not (yet) supported
        * lazy 'to-many' relations not yet supported
        * DB_LIMIT on children of lazy 'to-one' relations not yet supported
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
            try:
                value = o.__getattribute__(field)
            except AttributeError:
                value = None
            # object relation
            if IRelation.providedBy(col) and col.relation_type == 'to-one':
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
            elif IRelation.providedBy(col) and col.relation_type == 'to-many':
                continue
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
            cl.append(table.c[col] == val)
        return cl
    
    def _generate_query(self, q, table, mapping, params, joins = list(), 
                        order_by = dict()):
        params = params or dict()
        for attr, col in mapping.iteritems():
            value = params.get(attr, None)
            colname = col
            if IRelation.providedBy(col):
                if col.relation_type == 'to-one':
                    # in a to-one relation the id of the child is stored in the
                    # parent's table
                    colname = col.name
                    relname = 'id'
                else:
                    # in a to-many relation the id of the parent is stored 
                    # in the child's table
                    colname = 'id'
                    relname = col.name
            if IRelation.providedBy(col) and not value is DB_NULL:
                #(value is DB_NULL or isinstance(value, DB_LIMIT)): 
                # Object relation
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
                # assert not value or isinstance(value, dict)
                if col.lazy and value and '_id' in value.keys() \
                    and attr not in order_by.keys():
                    # in this case we got the id for the related object somehow
                    # but don't need the related object, as it's non-eagerly 
                    # loaded and not part of the ORDER_BY clause
                    q = q.where(table.c[colname] == value['_id'])
                else:
                    # related object is eagerly loaded or needed for the query
                    parent_col = table.c[colname]
                    rel_col = rel_tab.c[relname]
                    # TODO: very ugly... find a better way
                    # ensure the right order of JOIN clauses;
                    # add first table to joins on the left
                    if not joins:
                        joins = [[None, [table]]]
                    # check if current table is already in joins
                    if rel_tab in zip(*joins)[0]:
                        # yes: append clause
                        for k in xrange(len(joins)):
                            if joins[k][0] == rel_tab:
                                joins[k][1].append(parent_col == rel_col)
                    else:
                        # no, add class and clause
                        joins.append([rel_tab, [parent_col == rel_col]])
                    rel_order_by = order_by.get(attr, dict())
                    if isinstance(value, DB_LIMIT):
                        # column to maximize / minimize / fix
                        limit_col = col.cls.db_mapping[value.attr]
                        if value.type == 'fixed':
                            # select rows with given value only
                            q = q.where(rel_tab.c[limit_col] == value.value)
                        else: 
                            # select rows where limit_col is maximal / minimal 
                            rel_tabA = rel_tab.alias()
                            if value.type == 'max':
                                cl = rel_tab.c[limit_col] < rel_tabA.c[limit_col]
                            else:
                                cl = rel_tab.c[limit_col] > rel_tabA.c[limit_col]
                            joins.append([rel_tabA, 
                                         [and_(rel_col == rel_tabA.c[relname], 
                                               cl)
                                         ]])
                            q = q.where(rel_tabA.c[relname] == None)
                        value = None
                    q, joins = self._generate_query(q, rel_tab, 
                                                    col.cls.db_mapping, 
                                                    value, joins, 
                                                    rel_order_by)
            elif value == DB_NULL:
                q = q.where(table.c[colname] == None)
            elif isinstance(value, DB_LIKE):
                q = q.where(table.c[colname].like(value.value))
            elif value:
                q = q.where(table.c[colname] == value)
            # don't read lazy attribute columns
            if not ILazyAttribute.providedBy(col) and not \
                (IRelation.providedBy(col) and col.relation_type == 'to-many'):
                    q.append_column(table.c[colname])
                
        return q, joins
    
    def _generate_objs(self, cls, result, objs):
        table = cls.db_table
        values = dict()
        # set a default value for id
        cls.db_mapping.setdefault('_id', 'id')
        # init the object container for current object type
        objs.setdefault(cls, list())
        # get id of current obj
        try:
            cur_id = result[str(table) + '_' + cls.db_mapping['_id']]
        except NoSuchColumnError:
            cur_id = None
        if not cur_id:
            # skip empty objects
            return objs
        for attr, col in cls.db_mapping.iteritems():
            if IRelation.providedBy(col): # object relation
                if col.relation_type == 'to-one':
                    rel_id = result[str(table) + '_' + col.name]
                    if not rel_id:
                        # skip empty relation attributes
                        continue
                    if col.lazy:
                        values[attr] = col.cls()
                        if rel_id:
                            values[attr] = DbObjectProxy(self, col.cls, 
                                                         _id = rel_id)
                    else:
                        # use the object of type col.cls that was created last
                        rel_o = self._generate_objs(col.cls, 
                                                    result, objs)[col.cls]
                        if rel_o:
                            values[attr] = rel_o[-1]
                else: # to-many relation
                    rel_id = result[str(col.cls.db_table) + '_' + col.name]
                    rel_o = self._generate_objs(col.cls, result, objs)[col.cls]
                    values[attr] = list()
                    for o in rel_o:
                        rel_attr = o.__getattribute__(col.name + '_id')
                        if rel_attr and rel_attr == cur_id: 
                            values[attr].append(o)
            elif ILazyAttribute.providedBy(col): # lazy attribute
                values[attr] = DbAttributeProxy(self, col, table, {'id':
                                                result[str(table) + '_id']})
            else:
                values[attr] = result[str(table) + '_' + col]
        
        # check if object has already been created
        for o in objs[cls]:
            if values['_id'] == o._id:
                # yes, this should only happen on 'to-many' relations
                for key, val in values.iteritems():
                    o.__setattr__(key, val)
                return objs
        # no, create new object
        new_obj = cls()
        for key, val in values.iteritems():
            new_obj.__setattr__(key, val)
        objs[cls].append(new_obj)
        return objs
                
    
    def _get_children(self, obj):
        objs = list()
        to_many = list()
        for attr, col in obj.db_mapping.iteritems():
            if IRelation.providedBy(col):
                value = obj.__getattribute__(attr)
                if isinstance(value, list):
                    for v in value:
                        to_many.extend(self._get_children(v))
                elif value:
                    objs.extend(self._get_children(value))
        objs.append(obj)
        # add child objects last which correspond to a 'to-many' relation
        objs.extend(to_many)
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
        """
        Store a (list of) Serializable object(s) into specified DB table  
        if objs is a list, all objects in list will be stored within the same 
        transaction.
        
        @keyword cascading: If True, also underlying related objects are 
                            stored, default is False.
        @type cascading:    bool
        """
        if hasattr(self,'debug') and self.debug:
            start = time.time()
        cascading = kwargs.get('cascading', False)
        update = kwargs.get('update', False)
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
                if not update or not o._id:
                    r = conn.execute(table.insert(), **kwargs)
                    o._id = r.last_inserted_ids()[0]
                else:
                    w = (table.c[o.db_mapping['_id']] == o._id)
                    r = conn.execute(table.update(w), **kwargs)
                    # inform new children about object id by setting it again
                    o._id = o._id
            txn.commit()
        except IntegrityError, e:
            txn.rollback()
            raise DbError("Error storing an object.", e)
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Stored %i objects in %s seconds." %\
                  (len(objs), time.time()-start)
        return True
    
    def update(self, *objs, **kwargs):
        """
        Update a (list of) Serializable object(s).
        
        If objs is a list, all objects in list will be updated within the same 
        transaction. Objects to update have to provide an _id attribute to be 
        identified.
        
        @keyword cascading: If True, also underlying related objects are 
                            updated, default is False.
        @type cascading:    bool
        """
        kwargs['update'] = True
        self.store(*objs, **kwargs)
        

    def pickup(self, cls, **keys):
        """
        Read Serializable objects with given keys from database.
        @param cls: Object type to be retrieved.
        @keyword _order_by: dictionary of the form:  
            {'attribute':'ASC'|'DESC', ...}
        @keyword _limit: result limit
        @keyword _offset: result offset (used in combination with limit)
        @param **keys: kwarg list of the form: 
            - attribute_name = value
        or for relational attributes:
            - attribute_name = Object
            - attribute_name = {'attribute_name' : 'value'}
            
        In a to-many relation DB_LIMIT_MIN and DB_LIMIT_MAX may be used to 
        select only one single related object providing the maximum (or 
        minimum) for the given attribute:
            - relation_name = DB_LIMIT_MAX('attribute_name')
        
        Use DB_NULL as a value to force a column to be None; 
        attribute_name = None will be ignored:
            - attribute_name = DB_NULL
        """
        if hasattr(self,'debug') and self.debug:
            start = time.time()
        if not ISerializable.implementedBy(cls):
            raise DoesNotImplement(ISerializable)
        order_by = keys.get('_order_by', dict())
        limit = keys.get('_limit', None)
        offset = keys.get('_offset', None)
        table = cls.db_table
        map = cls.db_mapping
        # generate query
        q = table.select(use_labels = True)
        q, join_list = self._generate_query(q, table, map, keys, 
                                            order_by = order_by,
                                            joins = list())
        if join_list and len(join_list) >= 2:
            left_tab = join_list[0][1][0]
            joins = left_tab.outerjoin(join_list[1][0], 
                                       onclause = or_(*join_list[1][1]))
            del join_list[:2]
            for j in join_list:
                joins = joins.outerjoin(j[0], onclause = or_(*j[1]))
            q = q.select_from(joins)
        q = self._order_by(q, table, map, order_by)
        q = q.offset(offset).limit(limit)
        # execute query
        db = self.getDb()
        r = db.execute(q)
        try:
            results = r.fetchall()
        finally:
            r.close()
        # create objects from results
        objs = {cls:list()}
        for res in results:
            objs = self._generate_objs(cls, res, objs)
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Loaded %i object(-tree)s in %s seconds." %\
                  (len(objs[cls]), time.time()-start)
        return self._to_list(objs[cls])
    
    def drop(self, cls, **keys):
        """
        Delete object with given keys from database.
        
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
        ret = True
        # begin transaction:
        db = self.getDb()
        conn = db.connect()
        txn = conn.begin()
        try:
            w = self._where_clause(table, map, keys)
            # cascading deletes
            for rel in map.values():
                if IRelation.providedBy(rel) and rel.cascading_delete:
                    if rel.relation_type == 'to-one':
                        q = select([table.c[rel.name]], w)
                        relkey = '_id'
                    else:
                        # to-many relation
                        q = select([table.c['id']], w)
                        relkey = rel.name + '_id'
                    res = conn.execute(q).fetchall()
                    for r in res:
                        ret *= self.drop(rel.cls, **{relkey:r[0]})
            # delete parent
            result = conn.execute(table.delete(w))
            if not result.rowcount:
                ret *= False
            txn.commit()
        except:
            txn.rollback()
            raise
        finally:
            conn.close()
        if hasattr(self,'debug') and self.debug:
            print "DBUTIL: Deletion completed in %s seconds." %\
                  (time.time()-start)
        return ret


class Serializable(object):
    """
    Subclasses may be serialized into a DbStorage.
    
    Serializable objects should implement serializable attributes via the
    db_property descriptor.
    All arguments of the __init__ method of a Serializable object have to be 
    optional and should default to None!
    
    The db_mapping attribute is a dict of the following structure:
    db_mapping = {'attribute name' : 'name of column in db_table', ... }
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
        # set backreference ids:
        for name, col in self.db_mapping.iteritems():
            if IRelation.providedBy(col) and col.relation_type == 'to-many':
                objs = self.__getattribute__(name)
                if not objs:
                    continue
                if not isinstance(objs, list):
                    objs = [objs]
                for o in objs:
                    rel_attr = col.name + '_id'
                    o.__setattr__(rel_attr, id)
    
    _id = property(_getId, _setId, 'Internal id (integer)')


class DbObjectProxy(object):
    implements(IDbObjectProxy)
    
    def __init__(self, db_storage, cls, **kwargs):
        self.db_storage = db_storage
        cls.db_mapping.setdefault('_id', 'id')
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
    """
    @param attr: LazyAttribute instance
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
    """
    Use this property instead of the python 'property' descriptor to support 
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
#        if not hasattr(self, self.attr):
#            return property.__get__(self, obj, objtype)
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
    """
    Defines a one-to-one/many-to-one relation between Serializable objects.
    
    @param cls: class of target object type
    @param name: name of the referencing column in database table
    @param lazy: lazy getting of related objects (True by default), in order to
    support lazy getting, usage of the 'db_property' descriptor is mandatory.
    @param cascading_delete: automatically delete related objects, when parent
    is deleted (False by default)
    @param relation_type: 'to-one' | 'to-many'; Defines the relation type.
    Note: If set to 'to-one' name is a column in the referer's table, if set to
    'to-many' in the referee's table.
    """
    implements(IRelation)
    
    def __init__(self, cls, name, lazy = True, cascading_delete = False,
                 relation_type = 'to-one'):
        self.cls = cls
        self.name = name
        self.lazy = lazy
        self.cascading_delete = cascading_delete
        self.relation_type = relation_type
        if relation_type == 'to-many':
            # inject backreference attribute into db_mapping:
            cls.db_mapping.setdefault(name + '_id', name)


class LazyAttribute(object):
    """
    Defines a lazy object attribute.
    Loads a propertie's data not until attribute is accessed for the first 
    time.
    
    @param name: name of the database column holding attribute data 
    """
    implements(ILazyAttribute)
    
    def __init__(self, name):
        self.name = name
