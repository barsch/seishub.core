# -*- coding: utf-8 -*-

from sqlalchemy import MetaData, Table, Column, Integer, String, \
                       UniqueConstraint, ForeignKey, Text, Binary, \
                       PrimaryKeyConstraint, DateTime
DEFAULT_PREFIX = 'default_'
RESOURCE_TABLE = 'data'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
METADATA_TABLE = 'meta'
#METADATA_INDEX_TABLE = 'meta_idx'
URI_TABLE = 'uri'

# xmldbms tables:
metadata = MetaData()
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('data', Binary),
)

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
