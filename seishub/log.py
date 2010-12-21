# -*- coding: utf-8 -*-

from seishub.config import Option, BoolOption
from seishub.core import ERROR, WARN, INFO, DEBUG
from twisted.python import log, logfile
import os
import traceback
from glob import iglob


LOG_LEVELS = {'OFF': 0,
              'ERROR': ERROR,
              'WARN': WARN,
              'INFO': INFO,
              'DEBUG': DEBUG}


class Logger(object):
    """
    A log manager to handle all incoming log calls. 
    
    You still may use twisted.python.log.msg and twisted.python.log.err to 
    emit log messages.
    """

    Option('seishub', 'log_level', 'DEBUG',
        """Level of verbosity in log.

        Should be one of (`ERROR`, `WARN`, `INFO`, `DEBUG`).""")
    BoolOption('seishub', 'clear_logs_on_startup', False,
               "Clears logs at startup of SeisHub.")

    def __init__(self, env, log_file):
        self.env = env
        if log_file:
            log_path = os.path.join(env.getSeisHubPath(), 'logs')
            # clear log files
            if env.config.getbool('seishub', 'clear_logs_on_startup'):
                log_base = os.path.splitext(log_file)[0]
                for file in iglob(os.path.join(log_path, log_base + '.*')):
                    try:
                        os.remove(file)
                    except:
                        pass
            # new log file
            daily_log_file = logfile.DailyLogFile(log_file, log_path)
            env.app.setComponent(log.ILogObserver,
                                 log.FileLogObserver(daily_log_file).emit)
        self.start()

    def start(self):
        # log level
        log_level = self.env.config.get('seishub', 'log_level').upper()
        self.log_level = LOG_LEVELS.get(log_level, ERROR)

    def stop(self):
        for l in log.theLogPublisher:
            log.removeObserver(l)

    def _formatMessage(self, level, msg, showTraceback):
        if level:
            msg = '%s: %s' % (level, msg)
        log.msg(msg, isError=True)
        if showTraceback:
            log.msg(traceback.format_exc(), isError=True)

    def http(self, code, msg, showTraceback=False):
        if code < 400:
            self.debug(msg, showTraceback)
        elif code < 500:
            self.info(msg, showTraceback)
        else:
            self.error(msg, showTraceback)

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

    def log(self, msg, showTraceback=False):
        self._formatMessage('', msg, showTraceback)
