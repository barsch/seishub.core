# -*- coding: utf-8 -*-
"""
A SEED file monitor service.

This service synchronizes SEED files of any given directory with SeisHub's 
database. Modified files will be processed to retrieve additional quality 
information, e.g. number of gaps and overlaps. The quality information are 
computed using the L{obspy.mseed} wrapper for the libmseed library of 
C. Trabant (IRIS Data Management Center).

This service consists of two L{TimerService}s which are periodically called 
inside of the SeisHub service: 

(1) SEEDFileCrawler
  Searches periodically all given directories for MiniSEED files of a given 
  pattern. All files and their last modification time will be collected and 
  compared with the internal database. Modified files will be passed to the 
  L{SEEDFileMonitor} class via a watch list.. Files which have a recent 
  julian day and year combination in there filename (e.g. *.2009.002 for the 
  second day of year 2009) will be rescanned periodically.

(2) SEEDFileScanner 
  Scans all given files for MiniSEED information,, timing and data quality. 
  This service relies on the results of L{SEEDFileCrawler}.
"""

from seishub.config import BoolOption, ListOption, Option, IntOption
from seishub.defaults import SEEDFILEMONITOR_SCANNER_PERIOD, \
    SEEDFILEMONITOR_CRAWLER_PERIOD, SEEDFILEMONITOR_AUTOSTART, \
    SEEDFILEMONITOR_CRAWLER_FILE_CAP
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


class SEEDFileSerializer(object):
    """
    """

    def __init__(self, env):
        self.env = env
        self.watchlist = env.watchlist
        self.db = self.env.db.engine
        self._updateCurrentConfiguration()

    def _scan(self, path, file):
        """
        Gets header, gaps and overlap information of given MiniSEED file.
        """
        # skip if MiniSEED library is not available
        if not mseed:
            return {}
        filepath = str(os.path.join(path, file))
        result = {}
        # get header
        try:
            d = mseed.getFirstRecordHeaderInfo(filepath)
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
            gap_list = mseed.getGapList(filepath)
            result['DQ_gaps'] = len([g for g in gap_list if g[6] > 0])
            result['DQ_overlaps'] = len(gap_list) - result['DQ_gaps']
        except Exception, e:
            self.env.log.error('getGapList', str(e))
            pass
        # get start and end time
        try:
            (start, end) = mseed.getStartAndEndTime(filepath)
            result['start_datetime'] = \
                datetime.datetime.utcfromtimestamp(start.timestamp())
            result['end_datetime'] = \
                datetime.datetime.utcfromtimestamp(end.timestamp())
        except Exception, e:
            self.env.log.error('getStartAndEndTime', str(e))
            pass
        # quality flags
        try:
            data = mseed.getDataQualityFlagsCount(filepath)
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
            data = mseed.getTimingQuality(filepath)
            result['TQ_max'] = data.get('max', None)
            result['TQ_min'] = data.get('min', None)
            result['TQ_avg'] = data.get('average', None)
            result['TQ_median'] = data.get('median', None)
            result['TQ_uq'] = data.get('upper_quantile', None)
            result['TQ_lq'] = data.get('lower_quantile', None)
        except Exception, e:
            self.env.log.error('getTimingQuality', str(e))
            pass
        return result

    def _delete(self, path, file=None):
        """
        Remove a file or all files with a given path from the database.
        """
        sql_obj = miniseed_tab.delete()
        if file:
            sql_obj = sql_obj.where(sql.and_(miniseed_tab.c['file'] == file,
                                             miniseed_tab.c['path'] == path))
        else:
            sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
        try:
            self.db.execute(sql_obj)
            self.env.log.debugx('Deleting %s %s' % (path, file))
        except:
            pass

    def _insert(self, path, file, stats):
        """
        Add a new file into the database.
        """
        result = self._scan(path, file)
        sql_obj = miniseed_tab.insert().values(file=file, path=path,
                                               mtime=int(stats.st_mtime),
                                               size=stats.st_size, **result)
        try:
            self.db.execute(sql_obj)
            self.env.log.debugx('Inserting %s %s' % (path, file))
        except:
            pass

    def _update(self, path, file, stats):
        """
        Modify a file in the database.
        """
        result = self._scan(path, file)
        sql_obj = miniseed_tab.update()
        sql_obj = sql_obj.where(miniseed_tab.c['file'] == file)
        sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
        sql_obj = sql_obj.values(mtime=int(stats.st_mtime), size=stats.st_size,
                                 **result)
        try:
            self.db.execute(sql_obj)
            self.env.log.debugx('Updating %s %s' % (path, file))
        except Exception, e:
            self.env.log.error(str(e))
            pass

    def _select(self, path, file=None):
        """
        """
        if file:
            # check database for entry
            sql_obj = sql.select([miniseed_tab.c['mtime']],
                                 sql.and_(miniseed_tab.c['path'] == path,
                                          miniseed_tab.c['file'] == file))
            return self.db.execute(sql_obj).fetchone()
        else:
            sql_obj = sql.select([miniseed_tab.c['file'],
                                  miniseed_tab.c['mtime']],
                                 miniseed_tab.c['path'] == path)
            return dict(self.db.execute(sql_obj).fetchall())

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

    def _updateCurrentConfiguration(self):
        """
        """
        self.pattern = self.env.config.get('seedfilemonitor', 'pattern')
        self.scanner_period = self.env.config.getint('seedfilemonitor',
                                                     'scanner_period')
        paths = self.env.config.getlist('seedfilemonitor', 'paths')
        self.crawler_paths = [os.path.normcase(path) for path in paths]
        self.crawler_period = self.env.config.getint('seedfilemonitor',
                                                     'crawler_period')
        self.crawler_file_cap = self.env.config.getint('seedfilemonitor',
                                                       'crawler_file_cap')
        self.focus = self.env.config.getbool('seedfilemonitor',
                                             'focus_on_recent_files')
        # prepare file endings
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(1)
        self._today = today.strftime("%Y.%j")
        self._yesterday = yesterday.strftime("%Y.%j")

    def _hasPattern(self, file):
        """
        Checks if the file name fits to the preferred file pattern.
        """
        return fnmatch.fnmatch(file, self.pattern)

    def _removeFromWatchList(self, filepath):
        """
        Removes given file path from the watch list.
        """
        try:
            self.watchlist.remove(filepath)
        except ValueError:
            pass

    def _addToWatchList(self, filepath):
        """
        Adds a file path to the watch list avoiding duplicates.
        """
        if filepath not in self.watchlist:
            self.watchlist.append(filepath)


class SEEDFileScanner(internet.TimerService, SEEDFileSerializer):
    """
    A SEED file scanner.
    
    This class scans periodically all given MiniSEED files.
    """
    def __init__(self, env):
        SEEDFileSerializer.__init__(self, env)
        internet.TimerService.__init__(self, 60, self.iterate)

    def reset(self):
        """
        Resets the scanner parameters.
        """
        self._updateCurrentConfiguration()
        # work with copy of watch list to reach the reset page once a while
        self._files = copy.copy(self.watchlist)
        # set loop interval
        self._loop.interval = int(self.scanner_period)
        # logging
        self.env.log.debugx('Scanner restarted.')
        msg = "Scanner loop interval: %d s" % self._loop.interval
        self.env.log.debugx(msg)
        msg = "Watch list: %d files" % len(self._files)
        self.env.log.debugx(msg)

    def iterate(self):
        """
        Handles exactly one MiniSEED file.
        """
        try:
            filepath = self._files.pop()
        except IndexError:
            # end of list reached - restart crawling
            self.reset()
            return
        except AttributeError:
            # first loop after initialization - call reset
            self.reset()
            return
        path = os.path.dirname(filepath)
        file = os.path.basename(filepath)
        # remove files with wrong pattern
        if not self._hasPattern(file):
            self._delete(path, file)
            self._removeFromWatchList(filepath)
            return
        # get file stats
        try:
            stats = os.stat(filepath)
        except Exception, e:
            self.env.log.warn(str(e))
            self._removeFromWatchList(filepath)
            return
        # check database for entry
        db_file = self._select(path, file)
        if not db_file:
            # file does not exists -> add file
            self._insert(path, file, stats)
        elif int(stats.st_mtime) != db_file[0]:
            # modification time differs -> update file
            self._update(path, file, stats)
        # recent file - leave in watch list
        if self.focus:
            if file.endswith(self._today) or file.endswith(self._yesterday):
                return
        # finally remove from list
        self._removeFromWatchList(filepath)


class SEEDFileCrawler(internet.TimerService, SEEDFileSerializer):
    """
    A SEED file crawler.
    
    This class scans periodically all given paths for MiniSEED files and 
    collects them into a watch list.
    """
    def __init__(self, env):
        SEEDFileSerializer.__init__(self, env)
        internet.TimerService.__init__(self, 0.1, self.iterate)

    def reset(self):
        """
        Resets the crawler parameters.
        """
        self._updateCurrentConfiguration()
        # get search paths
        self._paths = []
        self._roots = copy.copy(self.crawler_paths)
        self._root = self._roots.pop()
        # create walker
        self._walker = os.walk(self._root, followlinks=True)
        # set loop interval
        self._loop.interval = max(int(self.crawler_period), 0.1)
        # logging
        self.env.log.debugx('Crawler restarted.')
        msg = "Crawler loop interval: %d s" % self._loop.interval
        self.env.log.debugx(msg)
        msg = "Crawling root '%s' ..." % self._root
        self.env.log.debug(msg)

    def iterate(self):
        """
        Handles exactly one directory.
        """
        # if watch list is pretty full - retry later
        if len(self.watchlist) > self.crawler_file_cap:
            return
        try:
            path, _, files = self._walker.next()
        except StopIteration:
            try:
                # get next search path
                self._root = self._roots.pop()
                # create walker
                self._walker = os.walk(self._root, followlinks=True)
                # logging
                msg = "Crawling root '%s' ..." % self._root
                self.env.log.debug(msg)
            except IndexError:
                # a whole cycle has been done - check paths
                db_paths = self._selectAllPaths()
                for path in db_paths:
                    # skip existing paths
                    if path in self._paths:
                        continue
                    # remove the others
                    self._delete(path)
                # reset everything
                self.reset()
            return
        except AttributeError:
            # first loop after initialization - call reset
            self.reset()
            return
        msg = "Scanning path '%s' ..." % path
        self.env.log.debugx(msg)
        # skip empty directories
        if not files:
            return
        # update path list
        if path not in self._paths:
            self._paths.append(path)
        # get all database entries for current path
        db_files = self._select(path)
        # check files
        for file in files:
            # skip file with wrong pattern
            if not self._hasPattern(file):
                continue
            # get file stats
            filepath = os.path.join(path, file)
            try:
                stats = os.stat(filepath)
            except Exception, e:
                self.env.log.warn(str(e))
                continue
            # compare with database entries
            if file not in db_files:
                # file does not exists -> add file
                self._addToWatchList(filepath)
                continue
            else:
                # check modification time
                if int(stats.st_mtime) != db_files[file]:
                    # modification time differs -> update file
                    self._addToWatchList(filepath)
                # remove from database files
                db_files.pop(file)
            # recent file - add to watch list
            if not self.focus:
                continue
            if file.endswith(self._today) or file.endswith(self._yesterday):
                self._addToWatchList(filepath)
        # remove remaining entries from database
        for file in db_files:
            self._delete(path, file)
            filepath = os.path.join(path, file)
            self._removeFromWatchList(filepath)


class SEEDFileMonitorService(service.MultiService):
    """
    A SEED file monitor service for SeisHub.
    """
    service_id = "seedfilemonitor"

    BoolOption('seedfilemonitor', 'autostart', SEEDFILEMONITOR_AUTOSTART,
        "Enable service on start-up.")
    ListOption('seedfilemonitor', 'paths', 'data',
        "List of file paths to scan for SEED files.")
    Option('seedfilemonitor', 'pattern', '*.*.*.*.*.*.*',
        "SEED file name pattern.")
    IntOption('seedfilemonitor', 'crawler_period',
        SEEDFILEMONITOR_CRAWLER_PERIOD, "Path check interval in seconds.")
    IntOption('seedfilemonitor', 'scanner_period',
        SEEDFILEMONITOR_SCANNER_PERIOD, "File check interval in seconds.")
    IntOption('seedfilemonitor', 'crawler_file_cap',
        SEEDFILEMONITOR_CRAWLER_FILE_CAP, "Maximum files in watch list.")
    BoolOption('seedfilemonitor', 'focus_on_recent_files', True,
        "Scanner focuses on recent files.")

    def __init__(self, env):
        self.env = env
        service.MultiService.__init__(self)
        self.setName('SEEDFileMonitor')
        self.setServiceParent(env.app)

        if not mseed:
            msg = "SEEDFileMonitorService needs obspy.mseed to parse " + \
                  "quality and timing information in MiniSEED files!"
            self.env.log.error(msg)

        # establish a shared file list instance in our environment
        env.watchlist = list()

        crawler = SEEDFileCrawler(env)
        crawler.setName("SEED File Crawler")
        self.addService(crawler)

        filemonitor = SEEDFileScanner(env)
        filemonitor.setName("SEED File Scanner")
        self.addService(filemonitor)

    def privilegedStartService(self):
        if self.env.config.getbool('seedfilemonitor', 'autostart'):
            service.MultiService.privilegedStartService(self)

    def startService(self):
        if self.env.config.getbool('seedfilemonitor', 'autostart'):
            service.MultiService.startService(self)

    def stopService(self):
        if self.running:
            # reset watch list
            self.env.watchlist = list()
            service.MultiService.stopService(self)
