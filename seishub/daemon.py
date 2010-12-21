"""
The SeisHub Daemon: platform-independent interface.
"""
from seishub.env import Environment
from seishub.services.manhole import ManholeService
from seishub.services.sftp import SFTPService
from seishub.services.ssh import SSHService
from seishub.services.web import WebService
from twisted.application import service
from twisted.python import usage
from twisted.scripts.twistd import _SomeApplicationRunner, ServerOptions
import sys


__all__ = ['run']


class SeisHubApplicationRunner(_SomeApplicationRunner):

    def __init__(self, config, log_file):
        _SomeApplicationRunner.__init__(self, config)
        self.log_file = log_file

    def createOrGetApplication(self):
        # create application
        application = service.Application("SeisHub")
        # setup our Environment
        env = Environment(application=application, log_file=self.log_file)
        # add services
        WebService(env)
        SSHService(env)
        ManholeService(env)
        SFTPService(env)
        #HeartbeatService(env)
        return application


def run():
    # parse daemon configuration
    config = ServerOptions()
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
    # start Twisted event loop
    SeisHubApplicationRunner(config, log_file).run()


if __name__ == '__main__':
    run()
