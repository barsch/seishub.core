from twisted.application import service
from twisted.python import log, logfile
#
class LogService(service.Service):
    def __init__(self, logName, logDir, logType, logRotate=False):
        self.logName = logName
        self.logDir = logDir
        self.maxLogSize = 1000000
        self.logType = logType
        self.logRotate = logRotate
    
    def startService(self):
        # logfile is a file-like object that supports rotation
        self.logFile = logfile.LogFile(
            self.logName, self.logDir, rotateLength=self.maxLogSize)
        # force rotation each time restarted (if enabled)
        if self.logRotate:
            self.logFile.rotate()
        if self.logType == "error":
            self.log = ErrorLog(self.logFile)
        else:
            self.log = AccessLog(self.logFile)
        self.log.start()

    def stopService(self):
        self.log.stop()
        self.logFile.close()
        del(self.logFile)


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
        
