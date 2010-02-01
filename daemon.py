# -*- test-case-name: twisted.test.test_twistd -*-
# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
The Twisted Daemon: platform-independent interface.

@author: Christopher Armstrong
"""
from obspy.core import read
from seishub.env import Environment
from seishub.services.manhole import ManholeService
from seishub.services.sftp import SFTPService
from seishub.services.ssh import SSHService
from seishub.services.waveformindexer import WaveformIndexerService
from seishub.services.web import WebService
from twisted.application import service
from twisted.python import usage
from twisted.python.runtime import platformType
import logging
import multiprocessing
import os
import pickle
import sys


if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner as _SomeApplicationRunner


__all__ = ['run']


class SeisHubApplicationRunner(_SomeApplicationRunner):

    def __init__(self, config, queues):
        _SomeApplicationRunner.__init__(self, config)
        self.queues = queues

    def createOrGetApplication(self):
        # create application
        application = service.Application("SeisHub")
        # setup our Environment
        env = Environment(application=application)
        # set queues
        env.queues = self.queues
        # add services
        WebService(env)
        SSHService(env)
        ManholeService(env)
        SFTPService(env)
        #HeartbeatService(env)
        WaveformIndexerService(env)
        return application


def worker(i, queues):
    logger = multiprocessing.log_to_stderr()
    logger.setLevel(logging.INFO)
    logger.info('Starting process ... %d' % i)
    (input_queue, output_queue) = queues
    for action, path, file, stats in iter(input_queue.get, 'STOP'):
        filepath = os.path.join(path, file)
        sys.stdout.write(filepath + '\n')
        try:
            stream = read(str(filepath))
            sys.stdout.write(str(stream) + '\n')
            del stream
            args = (action, path, file, stats)
            output_queue.put_nowait(args)
        except Exception, e:
            logger.info(str(e))
    logger.info('Stopping process ... %d' % i)


def run():

    # create file queue and worker processes
    NUMBER_OF_PROCESSORS = multiprocessing.cpu_count()
    input_queue = multiprocessing.Queue(NUMBER_OF_PROCESSORS * 2)
    output_queue = multiprocessing.Queue()
    queues = (input_queue, output_queue)
    for i in range(NUMBER_OF_PROCESSORS):
        p = multiprocessing.Process(target=worker, args=(i, queues))
        p.daemon = True
        p.start()
    # parse config
    config = ServerOptions()
    try:
        config.parseOptions()
    except usage.error, ue:
        print config
        print "%s: %s" % (sys.argv[0], ue)
    else:
        SeisHubApplicationRunner(config, queues).run()


if __name__ == '__main__':
    run()
