# -*- coding: utf-8 -*-

# default db settings
DEFAULT_DB_URI = 'sqlite:///db/seishub.db'

# default components
DEFAULT_COMPONENTS = ('seishub.services.admin.general.PluginsPanel',
                      'seishub.services.admin.general.ServicesPanel',
                      'seishub.services.ssh.general.ServicesCommand',
                      'seishub.packages.builtin.SeisHubPackage',
                      'seishub.packages.builtin.StylesheetResource',
                      'seishub.packages.builtin.SchemaResource',
                      'seishub.services.admin.themes.DefaultTheme')

ADMIN_PORT = 40443
ADMIN_CERTIFICATE = 'https.cert'
ADMIN_PRIVATE_KEY = 'https.private.key'
REST_PORT = 8080
SSH_PORT = 5001
SSH_PRIVATE_KEY = 'ssh.private.key'
SSH_PUBLIC_KEY = 'ssh.public.key'
SFTP_PORT = 5021
SFTP_PRIVATE_KEY = 'sftp.private.key'
SFTP_PUBLIC_KEY = 'sftp.public.key'
HEARTBEAT_CHECK_PERIOD = 20
HEARTBEAT_CHECK_TIMEOUT = 15
HEARTBEAT_HUBS = ['192.168.1.108', '192.168.1.109']
HEARTBEAT_UDP_PORT = 43278