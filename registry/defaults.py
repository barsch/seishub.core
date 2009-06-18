# -*- coding: utf-8 -*-

from seishub.db import DEFAULT_PREFIX
from seishub.db.manager import meta as metadata
from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint, Integer, \
    Text, Boolean, DateTime, Numeric


PACKAGES_TABLE = 'packages'
RESOURCETYPES_TABLE = 'resourcetypes'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'
ALIAS_TABLE = 'aliases'
MINISEED_TABLE = 'miniseed'


packages_tab = Table(DEFAULT_PREFIX + PACKAGES_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', Text),
    Column('version', Text),
    UniqueConstraint('name'),
    useexisting=True,
)

resourcetypes_tab = Table(DEFAULT_PREFIX + RESOURCETYPES_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', Text,),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id')),
    Column('version', Text),
    Column('version_control', Boolean),
    UniqueConstraint('name', 'package_id'),
    useexisting=True,
)

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('document_id', Integer, nullable=False),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id'),
           nullable=False),
    Column('resourcetype_id', Integer,
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('document_id', Integer, nullable=False),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id'),
           nullable=False),
    Column('resourcetype_id', Integer,
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

alias_tab = Table(DEFAULT_PREFIX + ALIAS_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id'),
           nullable=False),
    Column('resourcetype_id', Integer,
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('name', Text, nullable=False),
    Column('expr', Text, nullable=False),
    UniqueConstraint('package_id', 'resourcetype_id', 'name'),
    useexisting=True,
)

miniseed_tab = Table(DEFAULT_PREFIX + MINISEED_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('file', Text, nullable=False),
    Column('path', Text, nullable=False),
    Column('mtime', Integer, nullable=False),
    Column('size', Integer, nullable=False),
    Column('network_id', Text, nullable=True),
    Column('station_id', Text, nullable=True),
    Column('location_id', Text, nullable=True),
    Column('channel_id', Text, nullable=True),
    Column('start_datetime', DateTime, nullable=True),
    Column('end_datetime', DateTime, nullable=True),
    Column('DQ_gaps', Integer, nullable=True),
    Column('DQ_overlaps', Integer, nullable=True),
    Column('DQ_amplifier_saturation', Integer, nullable=True),
    Column('DQ_digitizer_clipping', Integer, nullable=True),
    Column('DQ_spikes', Integer, nullable=True),
    Column('DQ_glitches', Integer, nullable=True),
    Column('DQ_missing_or_padded_data', Integer, nullable=True),
    Column('DQ_telemetry_synchronization', Integer, nullable=True),
    Column('DQ_digital_filter_charging', Integer, nullable=True),
    Column('DQ_questionable_time_tag', Integer, nullable=True),
    Column('TQ_min', Numeric, nullable=True),
    Column('TQ_avg', Numeric, nullable=True),
    Column('TQ_max', Numeric, nullable=True),
    Column('TQ_median', Numeric, nullable=True),
    Column('TQ_lower_quantile', Numeric, nullable=True),
    Column('TQ_upper_quantile', Numeric, nullable=True),
    UniqueConstraint('file', 'path'),
    useexisting=True,
)
