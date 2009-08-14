# -*- coding: utf-8 -*-
"""
Default options for SeisHub.

Most options may be altered via the configuration file seishub.ini. So there is
no need to change values in here.
"""

import os


# default components
DEFAULT_COMPONENTS = ('seishub.packages.admin.web.general.PluginsPanel',
                      'seishub.packages.admin.web.general.ServicesPanel',
                      'seishub.packages.admin.web.general',
                      'seishub.packages.admin.ssh.general.ServicesCommand',
                      'seishub.packages.builtins',
                      'seishub.packages.admin.web.themes.MagicTheme')

MIN_PASSWORD_LENGTH = 8
ADMIN_THEME = 'magic'
DEFAULT_PAGES = ['index', 'index.html', 'index.htm']

HTTP_LOG_FILE = 'logs' + os.sep + 'http.log'
HTTPS_LOG_FILE = 'logs' + os.sep + 'https.log'
HTTP_PORT = 8080
HTTPS_PORT = 8443
HTTPS_CERT_FILE = 'conf' + os.sep + 'https.cert.pem'
HTTPS_PKEY_FILE = 'conf' + os.sep + 'https.pkey.pem'

SSH_AUTOSTART = False
SSH_PORT = 5001
SSH_PRIVATE_KEY = 'conf' + os.sep + 'ssh.private.key'
SSH_PUBLIC_KEY = 'conf' + os.sep + 'ssh.public.key'

SFTP_AUTOSTART = True
SFTP_PORT = 5021
SFTP_PRIVATE_KEY = 'conf' + os.sep + 'sftp.private.key'
SFTP_PUBLIC_KEY = 'conf' + os.sep + 'sftp.public.key'
SFTP_LOG_FILE = 'logs' + os.sep + 'sftp.log'

SEEDFILEMONITOR_AUTOSTART = False
SEEDFILEMONITOR_CRAWLER_FILE_CAP = 1000
SEEDFILEMONITOR_CRAWLER_PERIOD = 10
SEEDFILEMONITOR_SCANNER_PERIOD = 5

HEARTBEAT_AUTOSTART = False
HEARTBEAT_CHECK_PERIOD = 20
HEARTBEAT_CHECK_TIMEOUT = 15
HEARTBEAT_HUBS = ['192.168.1.108', '192.168.1.109']
HEARTBEAT_UDP_PORT = 43278

MANHOLE_AUTOSTART = False
MANHOLE_PORT = 5002
MANHOLE_PRIVATE_KEY = 'conf' + os.sep + 'manhole.private.key'
MANHOLE_PUBLIC_KEY = 'conf' + os.sep + 'manhole.public.key'
