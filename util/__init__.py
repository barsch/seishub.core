# -*- coding: utf-8 -*-
# module seishub.util

import datetime
from decimal import Decimal
import json as _json


class CustomJSONEncoder(_json.JSONEncoder):
    """ 
    """
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance (obj, datetime.timedelta):
            return str(obj)
        elif isinstance (obj, Decimal):
            return float(obj)
        else:
            return _json.JSONEncoder.default(self, obj)


def toJSON(data):
    return _json.dumps({'ResultSet': data},
                       cls=CustomJSONEncoder, indent=4)
