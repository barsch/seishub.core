# -*- coding: utf-8 -*-

from seishub.packages.interfaces import IMapper


class IRESTMapper(IMapper):
    """Extension point for adding URL mappings for the REST service."""
