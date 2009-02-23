# -*- coding: utf-8 -*-
"""
A SEED file monitor service.

This service synchronizes SEED files of any given directory with SeisHub's 
database. Modified files will be processed to retrieve additional quality 
information, e.g. gaps and overlaps. The quality information are computed
using the L{obspy.mseed} wrapper for the libmseed library of C. Trabant (IRIS 
Data Management Center).

This service consists of two L{TimerService}s which are periodically called 
inside of the SeisHub service: 

(1) SEEDFileCrawler
  Scans over time all given directories for any modifications and stores them 
  to the database. Files which have a recent julian day and year combination
  in there filename (e.g. *.2009.002 for the second day of year 2009) will 
  be collected for usage in the L{SEEDFileMonitor}.

(2) SEEDFileMonitor 
  Scans only specific SEED files where changes are expected. This service 
  relies on the results of L{SEEDFileCrawler}.
"""

from seishub.config import BoolOption, ListOption
from seishub.defaults import SEED_FILEMONITOR_AUTOSTART, \
    SEED_FILEMONITOR_CHECK_PERIOD
from seishub.registry.defaults import miniseed_tab
from sqlalchemy import sql
from twisted.application import internet, service
import copy
import datetime
import os


__all__ = ['SEEDFileMonitorService']


CRAWLER_INTERVAL = 0.1


class SEEDFileMonitor(internet.TimerService):
    """
    A SEED file monitor.
    
    This class scans periodically all given MiniSEED files.
    """
    def __init__(self, env, current_seed_files):
        self.current_seed_files = current_seed_files
        self.env = env
        self.db = self.env.db.engine
        self._files = []
        internet.TimerService.__init__(self, SEED_FILEMONITOR_CHECK_PERIOD, 
                                       self.iterate)
    
    def reset(self):
        """
        Resets the monitor parameters.
        """
        # copy of the current file list
        self._files = copy.copy(self.current_seed_files)
        # set interval dynamically
        num = len(self._files) or 1
        self._loop.interval = SEED_FILEMONITOR_CHECK_PERIOD / num
    
    def iterate(self):
        try:
            file=self._files.pop()
        except IndexError:
            self.reset()
            return
        print '-'
        fh = open(file, 'rb')
        data = fh.read()
        fh.close()
        print file, len(data)


class SEEDFileCrawler(internet.TimerService):
    """
    A SEED file crawler.
    
    This class scans periodically all given paths for MiniSEED files. 
    """
    def __init__(self, env, current_seed_files):
        self.env = env
        self.current_seed_files = current_seed_files
        self.db = self.env.db.engine
        self.reset()
        # call after all is initialized
        internet.TimerService.__init__(self, CRAWLER_INTERVAL, self.iterate)
    
    def reset(self):
        """
        Resets the crawler parameters.
        """
        paths = self.env.config.getlist('seed-filemonitor', 'paths')
        self._roots = [os.path.normcase(r) for r in paths]
        self._current_path =  self._roots.pop()
        self._current_walker = os.walk(self._current_path)
        self._all_paths = []
        # prepare file endings
        today = datetime.datetime.utcnow()
        self._today = today.strftime("%Y.%j")
        yesterday = today-datetime.timedelta(1)
        self._yesterday = yesterday.strftime("%Y.%j")
    
    def iterate(self):
        """
        This handles exactly one directory and all included files.
        """
        try:
            path, dirs, files = self._current_walker.next()
        except StopIteration:
            try:
                self._current_path = self._roots.pop()
                msg = "Scanning %s" % self._current_path
                self.env.log.info(msg)
                self._current_walker = os.walk(self._current_path)
            except IndexError:
                # a whole cycle has been done - check paths
                db_paths = self._selectAllPaths()
                for path in self._all_paths:
                    if path in db_paths:
                        db_paths.remove(path)
                # remove all left over paths
                for path in db_paths:
                    self._delete(path)
                # reset everything
                self.reset()
            return
        # skip directories with sub-directories
        if dirs:
            return
        # filter file names with wrong format
        files = [f for f in files if f.count('.')==6]
        # skip empty directories 
        if not files:
            return
        # update path list
        if path not in self._all_paths:
            self._all_paths.append(path)
        # check database for entries in current path
        sql_obj = sql.select([miniseed_tab.c.file, miniseed_tab.c.mtime], 
                             miniseed_tab.c.path==path)
        db_files = dict(self.db.execute(sql_obj).fetchall())
        # check files
        for file in files:
            # get file stats
            filepath = os.path.join(path, file)
            stats = os.stat(filepath)
            # compare with database entries
            if file not in db_files:
                # file does not exists -> add file
                self._insert(path, file, stats)
            else:
                if stats.st_mtime!=db_files[file]:
                    # modification time differs -> update file
                    self._update(path, file, stats)
                db_files.pop(file)
            # update relevant files for SEEDFileMonitor
            if file.endswith(self._today) or file.endswith(self._yesterday):
                if filepath not in self.current_seed_files:
                    self.current_seed_files.append(filepath)
            # XXX: process quality information
        # remove deleted files from db
        for file in db_files:
            self._delete(path, file)
    
    def _selectAllPaths(self):
        """
        Query for all paths inside the database.
        """
        sql_obj = sql.select([miniseed_tab.c.path]).distinct()
        try:
            result=self.db.execute(sql_obj)
        except:
            result=[]
        return [path[0] for path in result]
    
    def _delete(self, path, file=None):
        """
        Remove a file or all files with a given path from the database.
        """
        sql_obj = miniseed_tab.delete()
        if file:
            sql_obj = sql_obj.where(sql.and_(miniseed_tab.c.file==file,
                                             miniseed_tab.c.path==path))
        else:
            sql_obj = sql_obj.where(miniseed_tab.c.path==path)
        try:
            self.db.execute(sql_obj)
        except:
            pass
    
    def _insert(self, path, file, stats):
        """
        Add a new file into the database.
        """
        sql_obj = miniseed_tab.insert().values(file=file,
                                               path=path, 
                                               mtime=stats.st_mtime,
                                               size=stats.st_size)
        try:
            self.db.execute(sql_obj)
        except:
            pass

    def _update(self, path, file, stats):
        """
        Modify a file in the database.
        """
        sql_obj = miniseed_tab.update()
        sql_obj = sql_obj.where(miniseed_tab.c.file==file)
        sql_obj = sql_obj.where(miniseed_tab.c.path==path)
        sql_obj = sql_obj.values(mtime=stats.st_mtime,
                                 size=stats.st_size)
        try:
            self.db.execute(sql_obj)
        except:
            pass


class SEEDFileMonitorService(service.MultiService):
    """
    A SEED file monitor service for SeisHub.
    """
    BoolOption('seed-filemonitor', 'autostart', SEED_FILEMONITOR_AUTOSTART, 
        "Enable service on start-up.")
    ListOption('seed-filemonitor', 'paths', 'data', 
        "Paths to scan for SEED files.")
    
    def __init__(self, env):
        self.env = env
        service.MultiService.__init__(self)
        self.setName('SEED File Monitor')
        self.setServiceParent(env.app)
        
        current_seed_files = list()
        
        crawler = SEEDFileCrawler(env, current_seed_files)
        crawler.setName("SEED File Crawler")
        self.addService(crawler)
        
        filemonitor = SEEDFileMonitor(env, current_seed_files)
        filemonitor.setName("SEED File Monitor")
        self.addService(filemonitor)
    
    def privilegedStartService(self):
        if self.env.config.getbool('seed-filemonitor', 'autostart'):
            service.MultiService.privilegedStartService(self)
    
    def startService(self):
        if self.env.config.getbool('seed-filemonitor', 'autostart'):
            service.MultiService.startService(self)
    
    def stopService(self):
        if self.running:
            service.MultiService.stopService(self)