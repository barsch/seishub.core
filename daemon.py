"""
The SeisHub Daemon: platform-independent interface.
"""
from obspy.db.indexer import worker
from seishub.env import Environment
from seishub.services.manhole import ManholeService
from seishub.services.sftp import SFTPService
from seishub.services.ssh import SSHService
from seishub.services.waveformindexer import WaveformIndexerService
from seishub.services.web import WebService
from twisted.application import service
from twisted.python import usage
from twisted.python.runtime import platformType
import inspect
#import logging
import multiprocessing
import os
import sys


#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner as _SomeApplicationRunner


__all__ = ['run']


class SeisHubApplicationRunner(_SomeApplicationRunner):

    def __init__(self, config, queues, log_file):
        _SomeApplicationRunner.__init__(self, config)
        self.queues = queues
        self.log_file = log_file

    def createOrGetApplication(self):
        # create application
        application = service.Application("SeisHub")
        # setup our Environment
        env = Environment(application=application, log_file=self.log_file)
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


class SeisHubDaemonOptions(ServerOptions):
    optParameters = [
        ['number_of_cpus', 'c', multiprocessing.cpu_count(),
         "Number of CPU used for waveform indexing"]]


def run():
    # parse daemon configuration
    config = SeisHubDaemonOptions()
    try:
        config.parseOptions()
    except usage.error, ue:
        print config
        print "%s: %s" % (sys.argv[0], ue)
        return
    # debug modus
    if config['nodaemon']:
        log_file = None
    else:
        log_file = 'seishub.log'
    # get CPU count
    try:
        number_of_cpus = int(config['number_of_cpus'])
    except:
        number_of_cpus = multiprocessing.cpu_count()
    # hard code preview path
    src_path = inspect.getsourcefile(Environment)
    path = os.path.dirname(os.path.dirname(src_path))
    preview_path = os.path.join(path, 'db', 'preview')
    # create queues
    manager = multiprocessing.Manager()
    in_queue = manager.dict()
    work_queue = manager.list()
    out_queue = manager.list()
    queues = (in_queue, work_queue, out_queue)
    # create processes
    for i in range(number_of_cpus):
        args = (i, in_queue, work_queue, out_queue, preview_path)
        p = multiprocessing.Process(target=worker, args=args)
        p.daemon = True
        p.start()
    # start Twisted event loop
    SeisHubApplicationRunner(config, queues, log_file).run()


if __name__ == '__main__':
    run()
