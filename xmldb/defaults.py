# -*- coding: utf-8 -*-

from sqlalchemy import Table, Column, ForeignKey, Sequence  #@UnresolvedImport
from sqlalchemy import Integer, String, Text, Binary, Boolean #@UnresolvedImport
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint #@UnresolvedImport
from sqlalchemy.sql import func, text #@UnresolvedImport
                       
from seishub.db.dbmanager import meta as metadata
                       
DEFAULT_PREFIX = 'default_'
RESOURCE_TABLE = 'data'
RESOURCE_TYPE_TABLE = 'resource_types'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
QUERY_ALIASES_TABLE = 'query_aliases'
METADATA_TABLE = 'meta'
METADATA_DEF_TABLE = 'meta_def'
RESOURCE_META_TABLE = 'resource_meta'
XSD_TABLE = 'xsd'
XSLT_TABLE = 'xslt'

# xmldbms tables:
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('data', Binary),
    )

# XXX: sqlite does not support autoincrement on combined primary keys
resource_meta_tab = Table(DEFAULT_PREFIX + RESOURCE_META_TABLE, metadata,
    Column('id', Integer, autoincrement = True,
           default = text('(SELECT coalesce(max(id), 0) + 1 FROM '+\
                          DEFAULT_PREFIX + RESOURCE_META_TABLE +')')),
    Column('revision', Integer, autoincrement = True),
    Column('resource_id', Integer, 
           ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE + '.id'),
           ),
    Column('package_id', Text),
    Column('resourcetype_id', Text),
    Column('version_control', Boolean), 
    # Column('hash', Integer),
    PrimaryKeyConstraint('id', 'revision')
    )

metadata_def_tab = Table(DEFAULT_PREFIX + METADATA_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text),
    Column('type', Text)
    )

metadata_tab = Table(DEFAULT_PREFIX + METADATA_TABLE, metadata,
    Column('resource_id', Integer, ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE +
                                              '.id')),
    Column('metadata_id', Integer),
    Column('value', Text)
    )

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
#    Column('package_id', Text),
#    Column('resourcetype_id', Text),
    Column('value_path', Text),
    Column('key_path', Text),
    Column('data_type', String(20)),
    UniqueConstraint('value_path','key_path')
)

index_tab = Table(DEFAULT_PREFIX + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer, ForeignKey(DEFAULT_PREFIX + INDEX_DEF_TABLE +
                                           '.id')),
    Column('key', Text),
    Column('value', Integer),
)

query_aliases_tab = Table(DEFAULT_PREFIX + QUERY_ALIASES_TABLE, metadata,
    Column('name', Text, primary_key = True),
    Column('expr', Text)
)