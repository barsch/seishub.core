# -*- coding: utf-8 -*-

# default db settings
DEFAULT_DB_URI = "sqlite:///db/seishub.db"

# default components
DEFAULT_COMPONENTS = ('seishub.services.admin.general.PluginsPanel', \
                      'seishub.services.admin.general.ServicesPanel', )
DEFAULT_ADMIN_PORT = 40443
DEFAULT_HTTPS_CERTIFICATE_FILENAME = "https.cert"
DEFAULT_HTTPS_PRIVATE_KEY_FILENAME = "https.private.key"
DEFAULT_REST_PORT = 8080
DEFAULT_SSH_PORT = 5001
DEFAULT_SSH_PRIVATE_KEY_FILENAME = "ssh.private.key"
DEFAULT_SSH_PUBLIC_KEY_FILENAME = "ssh.public.key"