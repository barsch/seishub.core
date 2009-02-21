# -*- coding: utf-8 -*-

from seishub.config import BoolOption
from seishub.defaults import FILEMONITOR_AUTOSTART, FILEMONITOR_CHECK_PERIOD
from twisted.application.internet import TimerService
import os

__all__ = ['FileMonitorService']


class FileMonitorService(TimerService):
    """
    A MiniSEED filemonitor service for SeisHub.
    """
    BoolOption('filemonitor', 'autostart', FILEMONITOR_AUTOSTART, 
               "Enable service on start-up.")
    
    def __init__(self, env):
        self.i = 0
        self.env = env
        TimerService.__init__(self, FILEMONITOR_CHECK_PERIOD, self.walk)
        self.setName("FileMonitor")
        self.setServiceParent(env.app)
    
    def walk(self):
        print "walking ..."
        for root, dirs, files in os.walk('data'):
            if not files:
                continue
            print root, dirs, files
            for file in files:
                filepath = os.path.join(root, file)
                print file, os.path.getmtime(filepath), os.path.getsize(filepath)
    
    def privilegedStartService(self):
        if self.env.config.getbool('filemonitor', 'autostart'):
            TimerService.privilegedStartService(self)
    
    def startService(self):
        if self.env.config.getbool('filemonitor', 'autostart'):
            TimerService.startService(self)
