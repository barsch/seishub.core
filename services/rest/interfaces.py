# -*- coding: utf-8 -*-

from seishub.packages.interfaces import IResourceMapper


class IRESTMapper(IResourceMapper):
    """Extension point for adding URL mappings for the REST service."""
