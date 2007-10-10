# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.python import log, logfile

__all__ = ['LogService', 'ErrorLog', 'AccessLog']


class LogService(service.Service):
    def __init__(self, log_name, log_dir, log_type, log_rotate=False):
        self.log_name = log_name
        self.log_dir = log_dir
        # TODO: via config
        self.max_logsize = 1000000
        self.log_type = log_type
        self.log_rotate = log_rotate
    
    def startService(self):
        # logfile is a file-like object that supports rotation
        self.log_file = logfile.LogFile(
            self.log_name, self.log_dir, rotate_length=self.max_logsize)
        # force rotation each time restarted (if enabled)
        if self.log_rotate:
            self.log_file.rotate()
        if self.log_type == "error":
            self.log = ErrorLog(self.log_file)
        else:
            self.log = AccessLog(self.log_file)
        self.log.start()

    def stopService(self):
        self.log.stop()
        self.log_file.close()
        del(self.log_file)


class ErrorLog(log.FileLogObserver):
    def emit(self, logEntryDict):
        if not logEntryDict.get('isError'):
            return
        log.FileLogObserver.emit(self, logEntryDict)

class AccessLog(log.FileLogObserver):
    def emit(self, logEntryDict):
        if logEntryDict.get('isError'):
            return
        log.FileLogObserver.emit(self, logEntryDict)
        
