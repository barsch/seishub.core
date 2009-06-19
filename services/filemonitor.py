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

from seishub.config import BoolOption, ListOption, Option
from seishub.defaults import SEED_FILEMONITOR_AUTOSTART, \
    SEED_FILEMONITOR_CHECK_PERIOD
from seishub.registry.defaults import miniseed_tab
from sqlalchemy import sql
from twisted.application import internet, service
import copy
import datetime
import fnmatch
import os


try:
    from obspy.mseed import libmseed
    mseed = libmseed()
except:
    mseed = None


__all__ = ['SEEDFileMonitorService']


CRAWLER_INTERVAL = 1


class SEEDFileSerializer(object):
    """
    """

    def __init__(self, env):
        self.env = env
        self.db = self.env.db.engine

    def _scan(self, path, file):
        """
        Gets header, gaps and overlap information of given MiniSEED file.
        """
        if not mseed:
            return {}
        filename = str(os.path.join(path, file))
        result = {}
        # get header
        try:
            d = mseed.getFirstRecordHeaderInfo(filename)
            if d['station'] != '':
                result['station_id'] = d['station']
            if d['location'] != '':
                result['location_id'] = d['location']
            if d['channel'] != '':
                result['channel_id'] = d['channel']
            if d['network'] != '':
                result['network_id'] = d['network']
        except Exception, e:
            self.env.log.error('getFirstRecordHeaderInfo', str(e))
            pass
        # scan for gaps + overlaps
        try:
            gap_list = mseed.getGapList(filename)
            result['DQ_gaps'] = len([g for g in gap_list if g[6] > 0])
            result['DQ_overlaps'] = len(gap_list) - result['DQ_gaps']
        except Exception, e:
            self.env.log.error('getGapList', str(e))
            pass
        # get start and end time
        try:
            (start, end) = mseed.getStartAndEndTime(filename)
            result['start_datetime'] = \
                datetime.datetime.utcfromtimestamp(start.timestamp())
            result['end_datetime'] = \
                datetime.datetime.utcfromtimestamp(end.timestamp())
        except Exception, e:
            self.env.log.error('getStartAndEndTime', str(e))
            pass
        # quality flags
        try:
            data = mseed.getDataQualityFlagsCount(filename)
            if data and len(data) == 8:
                result['DQ_amplifier_saturation'] = data[0]
                result['DQ_digitizer_clipping'] = data[1]
                result['DQ_spikes'] = data[2]
                result['DQ_glitches'] = data[3]
                result['DQ_missing_or_padded_data'] = data[4]
                result['DQ_telemetry_synchronization'] = data[5]
                result['DQ_digital_filter_charging'] = data[6]
                result['DQ_questionable_time_tag'] = data[7]
        except Exception, e:
            self.env.log.error('getDataQualityFlagsCount', str(e))
            pass
        # timing quality
        try:
            data = mseed.getTimingQuality(filename)
            result['TQ_max'] = data.get('max', None)
            result['TQ_min'] = data.get('min', None)
            result['TQ_avg'] = data.get('average', None)
            result['TQ_Q2'] = data.get('median', None)
            result['TQ_Q3'] = data.get('upper_quantile', None)
            result['TQ_Q1'] = data.get('lower_quantile', None)
        except Exception, e:
            self.env.log.error('getTimingQuality', str(e))
            pass
        return result

    def _delete(self, path, file=None):
        """
        Remove a file or all files with a given path from the database.
        """
        self.env.log.debugx('Deleting %s %s' % (path, file))
        sql_obj = miniseed_tab.delete()
        if file:
            sql_obj = sql_obj.where(sql.and_(miniseed_tab.c['file'] == file,
                                             miniseed_tab.c['path'] == path))
        else:
            sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
        try:
            self.db.execute(sql_obj)
        except:
            pass

    def _insert(self, path, file, stats):
        """
        Add a new file into the database.
        """
        self.env.log.debugx('Inserting %s %s' % (path, file))
        result = self._scan(path, file)
        sql_obj = miniseed_tab.insert().values(file=file, path=path,
                                               mtime=int(stats.st_mtime),
                                               size=stats.st_size, **result)
        try:
            self.db.execute(sql_obj)
        except Exception, e:
            self.env.log.error(str(e))
            pass

    def _update(self, path, file, stats):
        """
        Modify a file in the database.
        """
        self.env.log.debugx('Updating %s %s' % (path, file))
        result = self._scan(path, file)
        sql_obj = miniseed_tab.update()
        sql_obj = sql_obj.where(miniseed_tab.c['file'] == file)
        sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
        sql_obj = sql_obj.values(mtime=int(stats.st_mtime), size=stats.st_size,
                                 **result)
        try:
            self.db.execute(sql_obj)
        except Exception, e:
            self.env.log.error(str(e))
            pass


class SEEDFileMonitor(internet.TimerService, SEEDFileSerializer):
    """
    A SEED file monitor.
    
    This class scans periodically all given MiniSEED files.
    """
    def __init__(self, env, current_seed_files=list()):
        SEEDFileSerializer.__init__(self, env)
        self.current_seed_files = current_seed_files
        self._files = []
        internet.TimerService.__init__(self, SEED_FILEMONITOR_CHECK_PERIOD,
                                       self.iterate)

    def reset(self):
        """
        Resets the monitor parameters.
        """
        self.pattern = self.env.config.get('seedfilemonitor', 'pattern')
        # copy of the current file list
        self._files = copy.copy(self.current_seed_files)
        # set interval dynamically
        num = len(self._files) or 1
        self._loop.interval = int(10 / num)
        msg = "Scanning %s ..." % self._files
        self.env.log.debugx(msg)
        msg = "Loop interval %d s" % self._loop.interval
        self.env.log.debugx(msg)
        # prepare file endings
        today = datetime.datetime.utcnow()
        self._today = today.strftime("%Y.%j")
        yesterday = today - datetime.timedelta(1)
        self._yesterday = yesterday.strftime("%Y.%j")

    def iterate(self):
        try:
            filepath = self._files.pop()
            path = os.path.dirname(filepath)
            file = os.path.basename(filepath)
        except IndexError:
            # end of list reached - restart crawling
            self.reset()
            return
        # remove files with wrong pattern
        if not fnmatch.fnmatch(file, self.pattern):
            self._delete(path, file)
            try:
                self.current_seed_files.remove(filepath)
            except KeyError:
                pass
            return
        # check database for entry
        sql_obj = sql.select([miniseed_tab.c['mtime']],
                             sql.and_(miniseed_tab.c['path'] == path,
                                      miniseed_tab.c['file'] == file))
        db_file = self.db.execute(sql_obj).fetchone()
        # get file stats
        try:
            stats = os.stat(filepath)
        except:
            # couldn't read the stats of this path
            return
        # compare with database entries
        if not db_file:
            # file does not exists -> add file
            self._insert(path, file, stats)
            return
        elif int(stats.st_mtime) != db_file[0]:
            # modification time differs -> update file
            self._update(path, file, stats)
            return
        elif file.endswith(self._today) or file.endswith(self._yesterday):
            # current file - needs to be updated
            return
        else:
            # remove remaining entries from database
            try:
                self.current_seed_files.remove(filepath)
            except KeyError:
                pass


class SEEDFileCrawler(internet.TimerService, SEEDFileSerializer):
    """
    A SEED file crawler.
    
    This class scans periodically all given paths for MiniSEED files. 
    """
    def __init__(self, env, current_seed_files=list()):
        SEEDFileSerializer.__init__(self, env)
        self.current_seed_files = current_seed_files
        self.reset()
        # call after all is initialized
        internet.TimerService.__init__(self, CRAWLER_INTERVAL, self.iterate)

    def reset(self):
        """
        Resets the crawler parameters.
        """
        # get current configuration
        paths = self.env.config.getlist('seedfilemonitor', 'paths')
        self.pattern = self.env.config.get('seedfilemonitor', 'pattern')
        self._roots = [os.path.normcase(r) for r in paths]
        self._current_path = self._roots.pop()
        msg = "Scanning '%s' ..." % self._current_path
        self.env.log.debug(msg)
        # start walking
        self._current_walker = os.walk(self._current_path, topdown=True,
                                       followlinks=True)
        self._all_paths = []
        # prepare file endings
        today = datetime.datetime.utcnow()
        self._today = today.strftime("%Y.%j")
        yesterday = today - datetime.timedelta(1)
        self._yesterday = yesterday.strftime("%Y.%j")

    def iterate(self):
        """
        This handles exactly one directory and all included files.
        """
        try:
            path, _, files = self._current_walker.next()
            msg = "Scanning '%s' ..." % path
            self.env.log.debugx(msg)
        except StopIteration:
            try:
                self._current_path = self._roots.pop()
                msg = "Scanning '%s' ..." % self._current_path
                self.env.log.debug(msg)
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
        # update path list
        if path not in self._all_paths:
            self._all_paths.append(path)
        # check database for entries in current path
        sql_obj = sql.select([miniseed_tab.c['file'], miniseed_tab.c['mtime']],
                             miniseed_tab.c['path'] == path)
        db_files = dict(self.db.execute(sql_obj).fetchall())
        # check files
        for file in files:
            # skip file with wrong pattern
            if not fnmatch.fnmatch(file, self.pattern):
                continue
            # get file stats
            filepath = os.path.join(path, file)
            stats = os.stat(filepath)
            # compare with database entries
            if file not in db_files:
                # file does not exists -> add file
                self.current_seed_files.append(filepath)
                continue
            else:
                # check modification time
                if int(stats.st_mtime) != db_files[file]:
                    # modification time differs -> update file
                    self.current_seed_files.append(filepath)
                db_files.pop(file)
            # filter and update current files for SEEDFileMonitor
            if file.endswith(self._today) or file.endswith(self._yesterday):
                if filepath not in self.current_seed_files:
                    self.current_seed_files.append(filepath)
        # remove remaining entries from database
        for file in db_files:
            self._delete(path, file)
            filepath = os.path.join(path, file)
            try:
                self.current_seed_files.remove(filepath)
            except KeyError:
                pass

    def _selectAllPaths(self):
        """
        Query for all paths inside the database.
        """
        sql_obj = sql.select([miniseed_tab.c['path']]).distinct()
        try:
            result = self.db.execute(sql_obj)
        except:
            result = []
        return [path[0] for path in result]


class SEEDFileMonitorService(service.MultiService):
    """
    A SEED file monitor service for SeisHub.
    """
    service_id = "seedfilemonitor"

    BoolOption('seedfilemonitor', 'autostart', SEED_FILEMONITOR_AUTOSTART,
        "Enable service on start-up.")
    ListOption('seedfilemonitor', 'paths', 'data',
        "List of file paths to scan for SEED files.")
    Option('seedfilemonitor', 'pattern', '*.*.*.*.*.*.*',
        "SEED file name pattern.")

    def __init__(self, env):
        self.env = env
        service.MultiService.__init__(self)
        self.setName('SEEDFileMonitor')
        self.setServiceParent(env.app)

        if not mseed:
            msg = "SEEDFileMonitorService needs obspy.mseed to parse gaps" + \
                  " and overlaps in miniseed files!"
            self.env.log.error(msg)

        # a shared file list instance
        shared_file_list = list()

        crawler = SEEDFileCrawler(env, shared_file_list)
        crawler.setName("SEED File Crawler")
        self.addService(crawler)

        filemonitor = SEEDFileMonitor(env, shared_file_list)
        filemonitor.setName("SEED File Monitor")
        self.addService(filemonitor)

    def privilegedStartService(self):
        if self.env.config.getbool('seedfilemonitor', 'autostart'):
            service.MultiService.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('seedfilemonitor', 'autostart'):
            service.MultiService.startService(self)

    def stopService(self):
        if self.running:
            service.MultiService.stopService(self)
