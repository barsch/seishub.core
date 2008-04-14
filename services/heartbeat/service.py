# -*- coding: utf-8 -*-

import time
import socket

from twisted.application import internet
from twisted.internet import protocol

from seishub.config import IntOption, ListOption, BoolOption
from seishub.defaults import HEARTBEAT_CHECK_PERIOD, HEARTBEAT_HUBS, \
                             HEARTBEAT_CHECK_TIMEOUT

HEARTBEAT_UDP_PORT = 43278


class HeartbeatProtocol(protocol.DatagramProtocol):
    """Receive UDP heartbeat packets and log them in a dictionary."""
    
    def __init__(self, env):
        self.env = env
    
    def datagramReceived(self, data, (ip, port)):
        if data=='SeisHub':
            # XXX: Check for version and given REST port
            self.env.nodes[ip] = [time.time(), data]


class HeartbeatDetector(internet.TimerService):
    """Detect clients not sending heartbeats and removes them from list."""
    
    def __init__(self, env):
        self.env = env
        internet.TimerService.__init__(self, HEARTBEAT_CHECK_PERIOD, self.detect)
    
    def detect(self):
        """Detects clients w/ heartbeat older than HEARTBEAT_CHECK_TIMEOUT."""
        limit = time.time() - HEARTBEAT_CHECK_TIMEOUT
        #silent = [ip for (ip, ipTime) in self.env.nodes.items() if ipTime < limit]
        self.env.log.debug('Active SeisHub nodes: %s' % self.env.nodes.items())


class HeartbeatTransmitter(internet.TimerService):
    """Sends heartbeat to list of active nodes."""

    def __init__(self, env):
        self.env = env
        internet.TimerService.__init__(self, HEARTBEAT_CHECK_PERIOD, self.transmit)
    
    def transmit(self):
        if len(self.env.nodes)==0:
            ips = self.env.config.getlist('heartbeat', 'default_hubs') or \
                  HEARTBEAT_HUBS
        else:
            ips = [node[0] for node in self.env.nodes.items()]
        for ip in ips:
            self.heartbeat(ip)
    
    def heartbeat(self, ip):
        hbsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hbsocket.sendto('SeisHub', (ip, HEARTBEAT_UDP_PORT))
        self.env.log.debug('Sending heartbeat to ' + ip + ':' + 
                           str(HEARTBEAT_UDP_PORT))


class HeartbeatReceiver(internet.UDPServer):
    
    def __init__(self, env):
        self.env = env
        internet.UDPServer.__init__(self, HEARTBEAT_UDP_PORT, 
                                    HeartbeatProtocol(env))


class HeartbeatService:
    """A asynchronous events-based heartbeat server for SeisHub."""
    
    IntOption('heartbeat', 'port', HEARTBEAT_UDP_PORT, 
              'Heartbeat port number.')
    ListOption('heartbeat', 'default_hubs', ','.join(HEARTBEAT_HUBS), 
               'Default IPs for very active SeisHub services.')
    BoolOption('heartbeat', 'active_node', 'on', 'Heartbeat status')
    
    def __init__(self, env):
        env.nodes = {}
        
        detector_service = HeartbeatDetector(env)
        detector_service.setName("Heartbeat Detector")
        detector_service.setServiceParent(env.app)
        
        transmitter_service = HeartbeatTransmitter(env)
        transmitter_service.setName("Heartbeat Transmitter")
        transmitter_service.setServiceParent(env.app)
        
        receiver_service = HeartbeatReceiver(env)
        receiver_service.setName("Heartbeat Receiver")
        receiver_service.setServiceParent(env.app)
