from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint  #@UnresolvedImport 
from sqlalchemy import Integer, Text, Boolean #@UnresolvedImport 
                       
from seishub.db.manager import meta as metadata

DEFAULT_PREFIX = 'default_'
PACKAGES_TABLE = 'packages'
RESOURCETYPES_TABLE = 'resourcetypes'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'
ALIAS_TABLE = 'aliases'

# XXX: use ForeignKey on all package_id and resourcetype_id cols
# XXX: SQLIte does not support ForeignKey constraints

packages_tab = Table(DEFAULT_PREFIX + PACKAGES_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text),
    Column('version', Text),
    UniqueConstraint('name'),
    useexisting=True,
)

resourcetypes_tab = Table(DEFAULT_PREFIX + RESOURCETYPES_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text,),
    Column('package_id', Integer, ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE +\
                                             '.id')),
    Column('version', Text), 
    Column('version_control', Boolean),
    UniqueConstraint('name', 'package_id'),
    useexisting=True,
)

## SQLite does not support foreign key constrints -> we use triggers instead
#resourcetypes_trigger = """
#CREATE TRIGGER fkd_%(fk)s_%(table)s_package_id
#  BEFORE DELETE ON %(table)s
#  FOR EACH ROW BEGIN
#      SELECT RAISE(ROLLBACK, 'delete on table "%(table)s" violates foreign key constraint "fk_%(table)s_package_id"')
#      WHERE (SELECT package_id FROM %(fk)s WHERE package_id = OLD.package_id) IS NOT NULL;
#  END;
#"""

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('document_id', Integer, nullable = False),
    Column('package_id', Integer, ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE +\
                                             '.id'), nullable = False),
    Column('resourcetype_id', Integer, 
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('document_id', Integer, nullable = False),
    Column('package_id', Integer, ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE +\
                                             '.id'), nullable = False),
    Column('resourcetype_id', Integer, 
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

alias_tab = Table(DEFAULT_PREFIX + ALIAS_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('package_id', Integer, ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE +\
                                             '.id'), nullable = False),
    Column('resourcetype_id', Integer, 
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('name', Text, nullable = False),
    Column('expr', Text, nullable = False),
    UniqueConstraint('package_id', 'resourcetype_id', 'name'),
    useexisting=True,
)