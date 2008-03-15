# -*- coding: utf-8 -*-

from sqlalchemy import MetaData, Table, Column, Integer, String, \
                       UniqueConstraint, ForeignKey, Text, Binary, \
                       PrimaryKeyConstraint, DateTime
                       
from seishub.db.dbmanager import meta as metadata
                       
DEFAULT_PREFIX = 'default_'
RESOURCE_TABLE = 'data'
RESOURCE_TYPE_TABLE = 'resource_types'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
QUERY_ALIASES_TABLE = 'query_aliases'
METADATA_TABLE = 'meta'
URI_TABLE = 'uri'

# xmldbms tables:
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('data', Binary),
    )

#resource_types_tab = Table(DEFAULT_PREFIX + RESOURCE_TYPE_TABLE, metadata,
#    Column('name', Text),
#    Column('type', Text),
#    Column('uri', Text, ForeignKey(DEFAULT_PREFIX + URI_TABLE +'.uri'),
#           primary_key = True),
#    )

uri_tab = Table(DEFAULT_PREFIX + URI_TABLE, metadata,
    Column('uri', Text),
    Column('revision', Integer),
    Column('res_id', Integer, ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE +
                                         '.id')),
    Column('res_type', Text),
    PrimaryKeyConstraint('uri','revision')
    )

metadata_tab = Table(DEFAULT_PREFIX + METADATA_TABLE, metadata,
                Column('res_id', Integer, 
                       ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE + '.id')),
                Column('user', Text),
                Column('timestamp', DateTime)
                )

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('key_path', Text),
    Column('value_path', Text),
    Column('data_type', String(20)),
    UniqueConstraint('key_path', 'value_path')
)

index_tab = Table(DEFAULT_PREFIX + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer, ForeignKey(DEFAULT_PREFIX + INDEX_DEF_TABLE +
                                           '.id')),
    Column('key', Text),
    Column('value', Text),
)

query_aliases_tab = Table(DEFAULT_PREFIX + QUERY_ALIASES_TABLE, metadata,
    Column('name', Text, primary_key = True),
    Column('expr', Text)
) 
