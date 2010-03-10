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
import os


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
        WAVEFORMINDEXER_CRAWLER_PERIOD, "Poll interval for file crawler in" + \
        " seconds.")
    BoolOption('waveformindexer', 'skip_dots', True,
        "Skips paths or files starting with a dot.")
    BoolOption('waveformindexer', 'cleanup', False,
        "Clean database from non-existing files or paths if activated, but" + \
        " will skip all paths marked as archived in the database.")

    def __init__(self, env):
        self.env = env
        # connect to database
        Base.metadata.create_all(self.env.db.engine, checkfirst=True)
        self.session = self.env.db.session
        self.log = self.env.log
        # service settings
        self.setName('WaveformIndexer')
        self.setServiceParent(env.app)
        # set queues
        self.input_queue = env.queues[0]
        self.work_queue = env.queues[1]
        self.output_queue = env.queues[2]
        self.log_queue = env.queues[3]
        # set initial options
        self.update()
        # start iterating
        self.crawler_period = float(self.env.config.get('waveformindexer',
                                    'crawler_period'))
        TimerService.__init__(self, self.crawler_period, self.iterate)

    def update(self):
        # options
        self.skip_dots = self.env.config.getbool('waveformindexer',
                                                 'skip_dots')
        self.cleanup = self.env.config.getbool('waveformindexer', 'cleanup')
        # search paths
        paths = self.env.config.getlist('waveformindexer', 'paths')
        paths = self._preparePaths(paths)
        for path in paths.keys():
            # avoid absolute paths
            if os.path.isabs(path):
                path = os.path.relpath(path, self.env.getSeisHubPath())
            # check path
            if not os.path.isdir(path):
                msg = "Skipping non-existing waveform path %s ..."
                self.env.log.warn(msg % path)
                # remove path
                paths.pop(path, True)
                continue
        self.paths = paths

    def privilegedStartService(self):
        if self.env.config.getbool('waveformindexer', 'autostart'):
            TimerService.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('waveformindexer', 'autostart'):
            TimerService.startService(self)

    def stopService(self):
        if self.running:
            TimerService.stopService(self)
