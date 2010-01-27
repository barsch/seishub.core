# -*- test-case-name: twisted.test.test_twistd -*-
# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
The Twisted Daemon: platform-independent interface.

@author: Christopher Armstrong
"""
from seishub.env import Environment
from seishub.services.manhole import ManholeService
from seishub.services.sftp import SFTPService
from seishub.services.ssh import SSHService
from seishub.services.waveformindexer import WaveformIndexerService
from seishub.services.web import WebService
from twisted.application import service
from twisted.python import log, usage
from twisted.python.runtime import platformType
import multiprocessing
import random
import sys
import time



if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner as _SomeApplicationRunner


__all__ = ['run']


class SeisHubApplicationRunner(_SomeApplicationRunner):
    def __init__(self, config, processes, queue):
        _SomeApplicationRunner.__init__(self, config)
        self.processes = processes
        self.queue = queue

    def createOrGetApplication(self):
        # create application
        application = service.Application("SeisHub")
        # setup our Environment
        env = Environment(application=application)
        env.processes = self.processes
        env.queue = self.queue
        # add services
        WebService(env)
        SSHService(env)
        ManholeService(env)
        SFTPService(env)
        #HeartbeatService(env)
        WaveformIndexerService(env)
        return application


import logging
logger = multiprocessing.log_to_stderr()
logger.setLevel(logging.DEBUG)
logger.warning('doomed')

def calculate(func, args, env):
    time.sleep(0.5 * random.random())
    logger.warning('Processed %s %s' % (func, args))


def worker(i, input, env):
    logger.warning('Start process ... %d' % i)
    for func, args in iter(input.get, 'STOP'):
        logger.warning('Process %d %s %s' % (i, func, args))
        calculate(func, args, env)
    logger.warning('Stop process ... %d' % i)


if __name__ == '__main__':
    # create file queue and worker processes
    queue = multiprocessing.Queue(20)
    processes = []
    for i in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=worker, args=(i, queue, None))
        p.daemon = True
        p.start()
        processes.append(p)
    # parse config
    config = ServerOptions()
    try:
        config.parseOptions()
    except usage.error, ue:
        print config
        print "%s: %s" % (sys.argv[0], ue)
    else:
        SeisHubApplicationRunner(config, processes, queue).run()
