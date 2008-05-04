# -*- coding: utf-8 -*-

from seishub.services.interfaces import IResourceMapper


class IRESTMapper(IResourceMapper):
    """Extension point for adding URL mappings for the REST service."""
