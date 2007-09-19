# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2006 Edgewall Software
# Copyright (C) 2003-2004 Jonas Borgström <jonas@edgewall.com>
# Copyright (C) 2006 Matthew Good <trac@matt-good.net>
# Copyright (C) 2005-2006 Christian Boos <cboos@neuf.fr>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>
#         Matthew Good <trac@matt-good.net>


# -- algorithmic utilities

try:
    reversed = reversed
except NameError:
    def reversed(x):
        if hasattr(x, 'keys'):
            raise ValueError('mappings do not support reverse iteration')
        i = len(x)
        while i > 0:
            i -= 1
            yield x[i]

try:
    sorted = sorted
except NameError:
    def sorted(iterable, cmp=None, key=None, reverse=False):
        """Partial implementation of the "sorted" function from Python 2.4"""
        if key is None:
            lst = list(iterable)
        else:
            lst = [(key(val), idx, val) for idx, val in enumerate(iterable)]
        lst.sort()
        if key is None:
            if reverse:
                return lst[::-1]
            return lst
        if reverse:
            lst = reversed(lst)
        return [i[-1] for i in lst]