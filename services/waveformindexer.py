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

from seishub.config import BoolOption, ListOption, IntOption, Option
from seishub.defaults import WAVEFORMINDEXER_CRAWLER_PERIOD, \
    WAVEFORMINDEXER_AUTOSTART, WAVEFORMINDEXER_QUEUESIZE
from seishub.registry.defaults import miniseed_tab
from sqlalchemy import sql
from twisted.application.internet import TimerService #@UnresolvedImport
from Queue import Empty as QueueEmpty, Full as QueueFull
import copy
import datetime
import fnmatch
import multiprocessing
import os
import pickle


ACTION_INSERT = 0
ACTION_UPDATE = 1

##XXX: remove
#try:
#    from obspy.mseed import LibMSEED
#    mseed = LibMSEED()
#except:
#    mseed = None
#
#
#__all__ = ['WaveformIndexerService']



#def _scan(env, path, file):
#    """
#    Gets header, gaps and overlap information of given MiniSEED file.
#    """
#    # skip if MiniSEED library is not available
#    if not mseed:
#        return {}
#    filepath = str(os.path.join(path, file))
#    result = {}
#    # get header
#    try:
#        d = mseed.getFirstRecordHeaderInfo(filepath)
#        if d['station'] != '':
#            result['station_id'] = d['station']
#        if d['location'] != '':
#            result['location_id'] = d['location']
#        if d['channel'] != '':
#            result['channel_id'] = d['channel']
#        if d['network'] != '':
#            result['network_id'] = d['network']
#    except Exception, e:
#        env.log.info('getFirstRecordHeaderInfo', str(e))
#        pass
#    # scan for gaps + overlaps
#    try:
#        gap_list = mseed.getGapList(filepath)
#        result['DQ_gaps'] = len([g for g in gap_list if g[6] > 0])
#        result['DQ_overlaps'] = len(gap_list) - result['DQ_gaps']
#    except Exception, e:
#        env.log.info('getGapList', str(e))
#        pass
#    # get start and end time
#    try:
#        (start, end) = mseed.getStartAndEndTime(filepath)
#        result['start_datetime'] = start.datetime
#        result['end_datetime'] = end.datetime
#    except Exception, e:
#        env.log.info('getStartAndEndTime', str(e))
#        pass
#    # quality flags
#    try:
#        data = mseed.getDataQualityFlagsCount(filepath)
#        if data and len(data) == 8:
#            result['DQ_amplifier_saturation'] = data[0]
#            result['DQ_digitizer_clipping'] = data[1]
#            result['DQ_spikes'] = data[2]
#            result['DQ_glitches'] = data[3]
#            result['DQ_missing_or_padded_data'] = data[4]
#            result['DQ_telemetry_synchronization'] = data[5]
#            result['DQ_digital_filter_charging'] = data[6]
#            result['DQ_questionable_time_tag'] = data[7]
#    except Exception, e:
#        env.log.info('getDataQualityFlagsCount', str(e))
#        pass
#    # timing quality
#    try:
#        data = mseed.getTimingQuality(filepath)
#        result['TQ_max'] = data.get('max', None)
#        result['TQ_min'] = data.get('min', None)
#        result['TQ_avg'] = data.get('average', None)
#        result['TQ_median'] = data.get('median', None)
#        result['TQ_uq'] = data.get('upper_quantile', None)
#        result['TQ_lq'] = data.get('lower_quantile', None)
#    except Exception, e:
#        env.log.info('getTimingQuality', str(e))
#        pass
#    return result
#
#
#class WaveformFileSerializer(object):
#    """
#    """
#
#    def __init__(self, env):
#        self.env = env
#        self.watchlist = env.watchlist
#        self.db = self.env.db.engine
#        self._updateCurrentConfiguration()
#
#    def _delete(self, path, file=None):
#        """
#        Remove a file or all files with a given path from the database.
#        """
#        if self.keep_files:
#            return
#        sql_obj = miniseed_tab.delete()
#        if file:
#            sql_obj = sql_obj.where(sql.and_(miniseed_tab.c['file'] == file,
#                                             miniseed_tab.c['path'] == path))
#        else:
#            sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
#        try:
#            self.db.execute(sql_obj)
#            self.env.log.debugx('Deleting %s %s' % (path, file))
#        except:
#            pass
#
#    def _select(self, path, file=None):
#        """
#        """
#        if file:
#            # check database for entry
#            sql_obj = sql.select([miniseed_tab.c['mtime']],
#                                 sql.and_(miniseed_tab.c['path'] == path,
#                                          miniseed_tab.c['file'] == file))
#            return self.db.execute(sql_obj).fetchone()
#        else:
#            sql_obj = sql.select([miniseed_tab.c['file'],
#                                  miniseed_tab.c['mtime']],
#                                 miniseed_tab.c['path'] == path)
#            return dict(self.db.execute(sql_obj).fetchall())
#
#    def _updateCurrentConfiguration(self):
#        """
#        """
#        self.patterns = self.env.config.get('waveformindexer', 'patterns')
#        self.scanner_period = self.env.config.getint('waveformindexer',
#                                                     'scanner_period')
#        paths = self.env.config.getlist('waveformindexer', 'paths')
#        self.crawler_paths = [os.path.normcase(path) for path in paths]
#        self.crawler_period = self.env.config.getint('waveformindexer',
#                                                     'crawler_period')
#        self.queue_size = self.env.config.getint('waveformindexer',
#                                                 'queue_size')
#        self.focus = self.env.config.getbool('waveformindexer',
#                                             'focus_on_recent_files')
#        self.keep_files = self.env.config.getbool('waveformindexer',
#                                                  'keep_files')
#        # prepare file endings
#        today = datetime.datetime.utcnow()
#        yesterday = today - datetime.timedelta(1)
#        self._today = today.strftime("%Y.%j")
#        self._yesterday = yesterday.strftime("%Y.%j")
#
#    def _hasPattern(self, file):
#        """
#        Checks if the file name fits to the preferred file pattern.
#        """
#        for pattern in self.patterns:
#            if fnmatch.fnmatch(file, pattern):
#                return True
#        return False
#
#    def _removeFromWatchList(self, filepath):
#        """
#        Removes given file path from the watch list.
#        """
#        try:
#            self.watchlist.remove(filepath)
#        except ValueError:
#            pass
#
#    def _addToWatchList(self, filepath):
#        """
#        Adds a file path to the watch list avoiding duplicates.
#        """
#        if filepath not in self.watchlist:
#            self.watchlist.append(filepath)
#
#
#class WaveformFileScanner(internet.TimerService, WaveformFileSerializer):
#    """
#    A SEED file scanner.
#    
#    This class scans periodically all given MiniSEED files.
#    """
#    def __init__(self, env):
#        WaveformFileSerializer.__init__(self, env)
#        internet.TimerService.__init__(self, 60, self.iterate)
#        # set number of extra processes
#        processes = self.env.config.get('waveformindexer', 'processes')
#        self.pool = multiprocessing.Pool(processes=processes)
#
#    def reset(self):
#        """
#        Resets the scanner parameters.
#        """
#        # skip if nothing to do
#        if not self.watchlist:
#            # but we set a safer loop interval
#            self._loop.interval = 30
#            return
#        self._updateCurrentConfiguration()
#        # handle first 100 files 
#        self._files = self.watchlist[0:100]
#        # set loop interval
#        self._loop.interval = int(self.scanner_period)
#
#    def iterate(self):
#        """
#        Handles exactly one MiniSEED file.
#        """
#        # skip if nothing to do
#        if not self.watchlist:
#            return
#        try:
#            filepath = self._files.pop()
#        except IndexError:
#            # end of list reached - restart crawling
#            self.reset()
#            return
#        except AttributeError:
#            # first loop after initialization - call reset
#            self.reset()
#            return
#        path = os.path.dirname(filepath)
#        file = os.path.basename(filepath)
#        # remove files with wrong pattern
#        if not self._hasPattern(file):
#            self._delete(path, file)
#            self._removeFromWatchList(filepath)
#            return
#        # get file stats
#        try:
#            stats = os.stat(filepath)
#        except Exception, e:
#            self.env.log.warn(str(e))
#            self._removeFromWatchList(filepath)
#            return
#        # check database for entry
#        db_file = self._select(path, file)
#        if not db_file:
#            # file does not exists -> add file
#            self._insert(path, file, stats)
#        elif int(stats.st_mtime) != db_file[0]:
#            # modification time differs -> update file
#            self._update(path, file, stats)
#        # recent file - leave in watch list
#        if self.focus:
#            if file.endswith(self._today) or file.endswith(self._yesterday):
#                return
#        # finally remove from list
#        self._removeFromWatchList(filepath)
#
#




class WaveformFileCrawler:
    """
    A waveform file crawler.
    
    This class scans periodically all given paths for waveform files and 
    collects them into a watch list.
    """

    def _scan(self, trace):
        """
        Gets header, gaps and overlap information of given trace object.
        """
        result = {}
        # get header
        result['station'] = trace.stats.station
        result['location'] = trace.stats.location
        result['channel'] = trace.stats.channel
        result['network'] = trace.stats.network
        result['starttime'] = trace.stats.starttime.datetime
        result['endtime'] = trace.stats.endtime.datetime
        result['calib'] = trace.stats.calib
        result['npts'] = trace.stats.npts
        result['sampling_rate'] = trace.stats.sampling_rate
        # quality flags
#        try:
#            data = mseed.getDataQualityFlagsCount(filepath)
#            if data and len(data) == 8:
#                result['DQ_amplifier_saturation'] = data[0]
#                result['DQ_digitizer_clipping'] = data[1]
#                result['DQ_spikes'] = data[2]
#                result['DQ_glitches'] = data[3]
#                result['DQ_missing_or_padded_data'] = data[4]
#                result['DQ_telemetry_synchronization'] = data[5]
#                result['DQ_digital_filter_charging'] = data[6]
#                result['DQ_questionable_time_tag'] = data[7]
#        except Exception, e:
#            env.log.info('getDataQualityFlagsCount', str(e))
#            pass
#        # timing quality
#        try:
#            data = mseed.getTimingQuality(filepath)
#            result['TQ_max'] = data.get('max', None)
#            result['TQ_min'] = data.get('min', None)
#            result['TQ_avg'] = data.get('average', None)
#            result['TQ_median'] = data.get('median', None)
#            result['TQ_uq'] = data.get('upper_quantile', None)
#            result['TQ_lq'] = data.get('lower_quantile', None)
#        except Exception, e:
#            env.log.info('getTimingQuality', str(e))
#            pass
        return result


    def _insert(self, path, file, stats, stream):
        """
        Add a new file into the database.
        """
        for trace in stream:
            result = self._scan(trace)
            sql_obj = miniseed_tab.insert().values(file=file, path=path,
                                                   mtime=int(stats.st_mtime),
                                                   size=stats.st_size,
                                                   **result)
            try:
                self.db.execute(sql_obj)
                self.env.log.debugx('Inserting %s %s' % (path, file))
            except:
                pass

    def _update(self, path, file, stats, stream):
        """
        Modify a file in the database.
        """
        for trace in stream:
            result = self._scan(trace)
            sql_obj = miniseed_tab.update()
            sql_obj = sql_obj.where(miniseed_tab.c['file'] == file)
            sql_obj = sql_obj.where(miniseed_tab.c['path'] == path)
            sql_obj = sql_obj.values(mtime=int(stats.st_mtime),
                                     size=stats.st_size, **result)
            try:
                self.db.execute(sql_obj)
                self.env.log.debugx('Updating %s %s' % (path, file))
            except Exception, e:
                self.env.log.error(str(e))
                pass

    def _delete(self, path, file=None):
        """
        Remove a file or all files with a given path from the database.
        """
        if self.keep_files:
            return
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

    def _updateCurrentConfiguration(self):
        """
        """
        self.patterns = self.env.config.getlist('waveformindexer', 'patterns')
        paths = self.env.config.getlist('waveformindexer', 'paths')
        self.crawler_paths = [os.path.normcase(path) for path in paths]
        self.crawler_period = float(self.env.config.get('waveformindexer',
                                                        'crawler_period'))
        self.focus = self.env.config.getbool('waveformindexer',
                                             'focus_on_recent_files')
        self.keep_files = self.env.config.getbool('waveformindexer',
                                                  'keep_files')
        self.queue_size = self.env.config.getint('waveformindexer',
                                                 'queue_size')
        self.number_of_processes = self.env.config.getint('waveformindexer',
                                                          'processes')
        # prepare file endings
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(1)
        self._today = today.strftime("%Y.%j")
        self._yesterday = yesterday.strftime("%Y.%j")

    def _hasPattern(self, file):
        """
        Checks if the file name fits to the preferred file pattern.
        """
        for pattern in self.patterns:
            if fnmatch.fnmatch(file, pattern):
                return True
        return False

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

    def _processQueue(self):
        try:
            action, path, file, stats = self.output_queue.get_nowait()
        except QueueEmpty:
            pass
        #else:
            # unpickle stream 
            #stream = pickle.loads(stream)
            #if action == ACTION_INSERT:
            #    self._insert(path, file, stats, stream)
            #else:
            #    self._update(path, file, stats, stream)

    def _resetWalker(self):
        """
        Resets the crawler parameters.
        """
        # update configuration
        self._updateCurrentConfiguration()
        # reset attributes
        self._current_path = None
        self._current_files = []
        self._db_files_in_current_path = []
        # get search paths for waveform crawler
        self._paths = []
        self._roots = copy.copy(self.crawler_paths)
        self._root = self._roots.pop()
        # create new walker
        self._walker = os.walk(self._root, topdown=True, followlinks=True)
        # set loop interval
        self._loop.interval = max(float(self.crawler_period), 0.1)
        # logging
        self.env.log.debugx('Crawler restarted.')
#        msg = "Current size of input queue: %d of %d files" % \
#            (self.input_queue.qsize(), self.input_queue.maxsize)
#        self.env.log.debugx(msg)
#        msg = "Current size of output queue: %d of %d files" % \
#            (self.output_queue.qsize(), self.output_queue.maxsize)
#        self.env.log.debugx(msg)
        msg = "Crawler loop interval: %.1f s" % self._loop.interval
        self.env.log.debugx(msg)
        self.env.log.debug("Crawling root '%s' ..." % self._root)

    def _stepWalker(self):
        """
        Steps current walker object to the next directory.
        """
        # try to fetch next directory
        try:
            self._current_path, _ , self._current_files = self._walker.next()
        except StopIteration:
            # finished cycling through all directories in current walker
            # remove remaining entries from database
            for file in self._db_files_in_current_path:
                self._delete(self._current_path, file)
            # try get next crawler search path
            try:
                self._root = self._roots.pop()
            except IndexError:
                # a whole cycle has been done - check paths
#                db_paths = self._selectAllPaths()
#                for path in db_paths:
#                    # skip existing paths
#                    if path in self._paths:
#                        continue
#                    # remove the others
#                    self._delete(path)
                # reset everything
                self._resetWalker()
                return
            # reset attributes
            self._current_path = None
            self._current_files = []
            self._db_files_in_current_path = []
            # create new walker
            self._walker = os.walk(self._root, topdown=True, followlinks=True)
            # logging
            self.env.log.debug("Crawling root '%s' ..." % self._root)
            return
        # logging
        self.env.log.debugx("Scanning path '%s' ..." % self._current_path)
        # skip empty directories
        if not self._current_files:
            return
        # get all database entries for current path
        self._db_files_in_current_path = self._select(self._current_path)

    def iterate(self):
        """
        Handles exactly one directory.
        """
        # skip if service is not running
        # be aware that the processor pool is still active waiting for work
        if not self.running:
            return
        # skip if input queue is full
        if self.input_queue.full():
            return
        # try to finalize a single processed stream object from output queue
        self._processQueue()
        # check for files which could not put into queue yet
        if self._not_yet_queued:
            try:
                self.input_queue.put_nowait(self._not_yet_queued)
            except QueueFull:
                # try later
                return
            self._not_yet_queued = None
        # walk through directories and files
        try:
            file = self._current_files.pop(0)
        except AttributeError:
            # first loop ever after initialization - call reset
            self._resetWalker()
            self._stepWalker()
            return
        except IndexError:
            # file list is empty - jump into next directory
            self._stepWalker()
            return
        # skip file with wrong pattern
        if not self._hasPattern(file):
            return
        # process a single file
        path = self._current_path
        filepath = os.path.join(path, file)
        # get file stats
        try:
            stats = os.stat(filepath)
        except Exception, e:
            self.env.log.warn(str(e))
            return
        # compare with database entries
        if file not in self._db_files_in_current_path:
            # file does not exists in database -> add file
            args = (ACTION_INSERT, path, file, stats)
            try:
                self.input_queue.put_nowait(args)
            except QueueFull:
                self._not_yet_queued = args
            return
        # file is already in database
        # -> compare modification times of current file with database entry
        # -> remove from file list so it won't be deleted on database cleanup
        db_file_mtime = self._db_files_in_current_path.pop(file)
        if int(stats.st_mtime) == db_file_mtime:
            return
        # modification time differs -> update file
        args = (ACTION_UPDATE, path, file, stats)
        try:
            self.input_queue.put_nowait(args)
        except QueueFull:
            self._not_yet_queued = args
        return


class WaveformIndexerService(TimerService, WaveformFileCrawler):
    """
    A waveform indexer service for SeisHub.
    """
    service_id = "waveformindexer"

    BoolOption('waveformindexer', 'autostart', WAVEFORMINDEXER_AUTOSTART,
        "Enable service on start-up.")
    ListOption('waveformindexer', 'paths', 'data',
        "List of file paths to scan for.")
    ListOption('waveformindexer', 'patterns', ['*.*.*.*.*.*.*'],
        "Waveform file name patterns.")
    Option('waveformindexer', 'crawler_period',
        WAVEFORMINDEXER_CRAWLER_PERIOD, "Path check interval in seconds.")
    IntOption('waveformindexer', 'queue_size',
        WAVEFORMINDEXER_QUEUESIZE, "Maximum size of the file queue.")
    BoolOption('waveformindexer', 'focus_on_recent_files', True,
        "Scanner focuses on recent files.")
    BoolOption('waveformindexer', 'keep_files', False,
        "Clean-up database from missing files.")
    IntOption('waveformindexer', 'processes', multiprocessing.cpu_count(),
        "The number of spawned processes used by the service.")

    def __init__(self, env):
        self.env = env
        self.db = self.env.db.engine
        self._updateCurrentConfiguration()
        # service settings
        self.setName('WaveformIndexer')
        self.setServiceParent(env.app)
        # set queues
        self.input_queue = env.queues[0]
        self.output_queue = env.queues[1]
        self._not_yet_queued = None
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
