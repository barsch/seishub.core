# -*- coding: utf-8 -*-

import os
from twisted.python import log, logfile

LOG_LEVELS = ['ERROR','WARN','INFO','DEBUG','ALL']


class ErrorLog(log.FileLogObserver):
    def emit(self, eventDict):
        if not eventDict["isError"]:
            return
        log.FileLogObserver.emit(self, eventDict)


class AccessLog(log.FileLogObserver):
    def emit(self, eventDict):
        if eventDict["isError"]:
            return
        log.FileLogObserver.emit(self, eventDict)


class Logger(object):
    """A log manager to handle all incoming log calls. You still may use 
    twisted.python.log.msg and twisted.python.log.err to emit log messages.
    """
    def __init__(self, env):
        # init new log
        self.env = env
        self.start()
    
    def start(self):
        log_dir = os.path.join(self.env.path, 'log')
        
        # Get log level
        if self.env.log_level.upper() in LOG_LEVELS:
            self.log_level = LOG_LEVELS.index(self.env.log_level.upper())
        else:
            self.log_level = 0
        
        # Error log
        errlog_file = self.env.error_log_file
        self.errlog_handler = logfile.LogFile(errlog_file, log_dir, 
                                              rotateLength=100000)
        self.errlog_handler.rotate() 
        self.errlog = ErrorLog(self.errlog_handler)
        self.errlog.start()
        
        # Access log
        acclog_file = self.env.access_log_file
        self.acclog_handler = logfile.LogFile(acclog_file, log_dir, 
                                              rotateLength=100000)
        self.acclog_handler.rotate()
        self.acclog = AccessLog(self.acclog_handler)
        self.acclog.start()
    
    def stop(self):
        for l in log.theLogPublisher:
            log.removeObserver(l)
    
    def error(self, msg, exception=None):
        if exception:
            log.err(exception, 'ERROR: %s' % msg)
        else:
            log.msg('ERROR: %s' % msg, isError=True)
    
    def warn(self, msg, exception=None):
        if self.log_level<1:
            return
        if exception:
            log.err(exception, 'WARN: %s' % msg)
        else:
            log.msg('WARN: %s' % msg, isError=True)
    
    def info(self, msg, exception=None):
        if self.log_level<2:
            return
        if exception:
            log.err(exception, 'INFO: %s' % msg)
        else:
            log.msg('INFO: %s' % msg, isError=True)
    
    def msg(self, msg):
        log.msg(msg, isError=True)
    
    def debug(self, msg):
        if self.log_level<3:
            return
        log.msg('DEBUG: %s' % msg, isError=True)
