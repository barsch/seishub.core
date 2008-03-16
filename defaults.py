# -*- coding: utf-8 -*-

# default db settings
DEFAULT_DB_URI = "sqlite:///db/seishub.db"

# default components
DEFAULT_COMPONENTS = ('seishub.services.admin.general.PluginsPanel', \
                      'seishub.services.admin.general.ServicesPanel', )
DEFAULT_ADMIN_PORT = 40443
DEFAULT_REST_PORT = 8080
DEFAULT_TELNET_PORT = 5001