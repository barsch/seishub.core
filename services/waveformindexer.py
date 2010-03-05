# -*- coding: utf-8 -*-
"""
A waveform indexer service.

This service synchronizes waveform files of any given directory with SeisHub's 
database. Modified files will be processed to retrieve additional quality 
information, e.g. number of gaps and overlaps.
"""

from obspy.db.db import Base
from obspy.db.indexer import WaveformFileCrawler
from seishub.config import BoolOption, ListOption, Option
from seishub.defaults import WAVEFORMINDEXER_CRAWLER_PERIOD, \
    WAVEFORMINDEXER_AUTOSTART
from twisted.application.internet import TimerService #@UnresolvedImport


class WaveformIndexerService(TimerService, WaveformFileCrawler):
    """
    A waveform indexer service for SeisHub.
    """
    service_id = "waveformindexer"

    BoolOption('waveformindexer', 'autostart', WAVEFORMINDEXER_AUTOSTART,
        "Enable service on start-up.")
    ListOption('waveformindexer', 'paths', 'data=*.*',
        "List of file paths to scan for.")
    Option('waveformindexer', 'crawler_period',
        WAVEFORMINDEXER_CRAWLER_PERIOD, "Path check interval in seconds.")
    BoolOption('waveformindexer', 'skip_dots', True,
        "Scanner focuses on recent files.")
    BoolOption('waveformindexer', 'cleanup', False,
        "Clean-up database from missing files.")

    def __init__(self, env):
        self.env = env
        # connect to database
        metadata = Base.metadata
        metadata.create_all(self.env.db.engine, checkfirst=True)
        self.session = self.env.db.session()
        # options
        self.skip_dots = env.config.getbool('waveformindexer', 'skip_dots')
        self.cleanup = env.config.getbool('waveformindexer', 'cleanup')
        self.crawler_period = float(env.config.get('waveformindexer',
                                                   'crawler_period'))
        self.log = self.env.log
        # service settings
        self.setName('WaveformIndexer')
        self.setServiceParent(env.app)
        # set queues
        self.input_queue = env.queues[0]
        self.work_queue = env.queues[1]
        self.output_queue = env.queues[2]
        # config
        import os
        path = os.path.normpath('C:\\Users\\barsch\\Workspace\\seishub\\trunk\\data')
        self.paths = {path:['*.*']}
        # start iterating
        TimerService.__init__(self, self.crawler_period, self.iterate)

    def privilegedStartService(self):
        if self.env.config.getbool('waveformindexer', 'autostart'):
            TimerService.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('waveformindexer', 'autostart'):
            TimerService.startService(self)

    def stopService(self):
        if self.running:
            TimerService.stopService(self)
