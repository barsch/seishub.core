from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint  #@UnresolvedImport 
from sqlalchemy import Integer, Text, Boolean #@UnresolvedImport 
                       
from seishub.db.dbmanager import meta as metadata

DEFAULT_PREFIX = 'default_'
PACKAGES_TABLE = 'packages'
RESOURCETYPES_TABLE = 'resourcetypes'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'
ALIAS_TABLE = 'aliases'

# XXX: use ForeignKey on all package_id and resourcetype_id cols

packages_tab = Table(DEFAULT_PREFIX + PACKAGES_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text,),
    Column('version', Text),
    UniqueConstraint('name')
)

resourcetypes_tab = Table(DEFAULT_PREFIX + RESOURCETYPES_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text,),
    Column('package_id', Integer, ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE +\
                                             '.id')),
    Column('version', Text), 
    Column('version_control', Boolean),
    UniqueConstraint('name', 'package_id')
)

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('resource_id', Text, nullable = False),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type')
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('resource_id', Text, nullable = False),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type')
)

alias_tab = Table(DEFAULT_PREFIX + ALIAS_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('name', Text, nullable = False),
    Column('expr', Text, nullable = False),
    UniqueConstraint('package_id', 'resourcetype_id', 'name'),
)