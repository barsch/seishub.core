#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor 

from seishub.env import Environment
from seishub.services.admin import AdminServiceFactory
from seishub.defaults import HTTP_PORT, SSH_PORT, SFTP_PORT
from seishub.services.web import WebServiceFactory
from seishub.services.ssh import SSHServiceFactory
from seishub.services.sftp import SFTPServiceFactory


def main():
    # setup our Environment
    env=Environment()
    
    # Twisted
    application = service.Application("SeisHub")
    env.app = application
    
    ## Admin
    port = env.config.getint('admin', 'port') or 40443
    reactor.listenTCP(port, AdminServiceFactory(env)) #@UndefinedVariable
    
    ## REST
    port = env.config.getint('web', 'http_port') or HTTP_PORT
    reactor.listenTCP(port, WebServiceFactory(env)) #@UndefinedVariable
    
    ## SSH
    port = env.config.getint('ssh', 'port') or SSH_PORT
    reactor.listenTCP(port, SSHServiceFactory(env)) #@UndefinedVariable
    
    ## SSH
    port = env.config.getint('sftp', 'port') or SFTP_PORT
    reactor.listenTCP(port, SFTPServiceFactory(env)) #@UndefinedVariable
    
    reactor.run() #@UndefinedVariable


if __name__ == '__main__':
    statement = 'main()'
    filename='output.pstats' 
    sort=-1
    import os, tempfile, hotshot, hotshot.stats
    logfd, logfn = tempfile.mkstemp()
    prof = hotshot.Profile(logfn)
    prof = prof.run(statement)
    prof.close()
    stats = hotshot.stats.load(logfn)
    stats.strip_dirs()
    stats.sort_stats(sort)
    result = stats.dump_stats(filename)
