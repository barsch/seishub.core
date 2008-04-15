# -*- coding: utf-8 -*-

import os
import traceback

from twisted.python import log, logfile

from seishub.core import ERROR, WARN, INFO, DEBUG
from seishub.config import Option, IntOption


LOG_LEVELS = {'OFF': -1,
              'ERROR': ERROR,
              'WARN': WARN,
              'INFO': INFO,
              'DEBUG': DEBUG}


class ErrorLog(log.FileLogObserver):
    """Error log only for logging error messages."""
    
    def emit(self, eventDict):
        #skip access messages
        if not eventDict["isError"]:
            return
        log.FileLogObserver.emit(self, eventDict)


class AccessLog(log.FileLogObserver):
    """Access log for logging non errors."""
    
    def emit(self, eventDict):
        #skip error messages
        if eventDict["isError"]:
            return
        log.FileLogObserver.emit(self, eventDict)


class Logger(object):
    """A log manager to handle all incoming log calls. You still may use 
    twisted.python.log.msg and twisted.python.log.err to emit log messages.
    """
    
    Option('logging', 'error_log_file', 'error.log',
        """If `log_type` is `file`, this should be a the name of the file.""")
    
    Option('logging', 'access_log_file', 'access.log',
        """If `log_type` is `file`, this should be a the name of the file.""")
    
    Option('logging', 'log_level', 'DEBUG',
        """Level of verbosity in log.
        
        Should be one of (`ERROR`, `WARN`, `INFO`, `DEBUG`).""")
    IntOption('logging', 'log_size', 1024*1024,
        """File size in bytes that triggers the server to move old logs to a 
        separate file.""")
    
    def __init__(self, env):
        # init new log
        self.env = env
        self.start()
    
    def start(self):
        log_dir = os.path.join(self.env.config.path, 'log')
        
        # Get log level and rotation size
        log_level = self.env.config.get('logging', 'log_level').upper()
        log_size = self.env.config.get('logging', 'log_size')
        self.log_level = LOG_LEVELS.get(log_level, ERROR)
        
        # Error log
        errlog_file = self.env.config.get('logging', 'error_log_file')
        self.errlog_handler = logfile.LogFile(errlog_file, log_dir, 
                                              rotateLength=log_size)
        self.errlog = ErrorLog(self.errlog_handler)
        self.errlog.start()
        
        # Access log
        acclog_file = self.env.config.get('logging', 'access_log_file')
        self.acclog_handler = logfile.LogFile(acclog_file, log_dir, 
                                              rotateLength=log_size)
        self.acclog = AccessLog(self.acclog_handler)
        self.acclog.start()
    
    def stop(self):
        for l in log.theLogPublisher:
            log.removeObserver(l)
    
    def _formatMessage(self, level, msg, showTraceback):
        log.msg('%s %s' % (level, msg), isError=True)
        if showTraceback:
            log.msg(traceback.format_exc(), isError=True)
    
    def error(self, msg, showTraceback=False):
        if self.log_level < ERROR:
            return
        self._formatMessage('ERROR', msg, showTraceback)
        
    def warn(self, msg, showTraceback=False):
        if self.log_level < WARN:
            return
        self._formatMessage('WARN', msg, showTraceback)
    
    def info(self, msg, showTraceback=False):
        if self.log_level < INFO:
            return
        self._formatMessage('INFO', msg, showTraceback)
    
    def debug(self, msg, showTraceback=False):
        if self.log_level < DEBUG:
            return
        self._formatMessage('DEBUG', msg, showTraceback)
