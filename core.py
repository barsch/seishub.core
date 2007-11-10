# -*- coding: utf-8 -*-

__all__ = ['SeishubError']


class SeishubError(Exception):
    """Exception base class for errors in Seishub."""

    def __init__(self, message, title=None, show_traceback=False):
        Exception.__init__(self, message)
        self.message = message
        self.title = title
        self.show_traceback = show_traceback


