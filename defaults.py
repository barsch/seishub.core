# -*- coding: utf-8 -*-

import os

# default db settings
DEFAULT_DB_URI = 'sqlite:///db/seishub.db'

# default components
DEFAULT_COMPONENTS = ('seishub.services.web.admin.general.PluginsPanel',
                      'seishub.services.web.admin.general.ServicesPanel',
                      'seishub.services.web.admin.general',
                      'seishub.services.ssh.general.ServicesCommand',
                      'seishub.packages.builtins',
                      'seishub.services.web.admin.themes.MagicTheme')

MIN_PASSWORD_LENGTH = 5
ADMIN_THEME = 'magic'

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

HEARTBEAT_AUTOSTART = False
HEARTBEAT_CHECK_PERIOD = 20
HEARTBEAT_CHECK_TIMEOUT = 15
HEARTBEAT_HUBS = ['192.168.1.108', '192.168.1.109']
HEARTBEAT_UDP_PORT = 43278