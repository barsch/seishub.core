# -*- coding: utf-8 -*-

class DbEnabled(object):
    """Mixin providing access to database manager"""
    def __init__(self, db):
        self._set_db(db)

    def _set_db(self, db):
        self._db = db.engine