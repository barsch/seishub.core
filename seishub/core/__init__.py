# -*- coding: utf-8 -*-

"""
SeisHub - Archiving, processing and simulation of multi-component data in 
seismology using Web Services

U{http://www.seishub.org/}

@author: Robert Barsch <barsch@lmu.de>
@author: Paul Käufl <paul.kaeufl@geophysik.uni-muenchen.de>
"""
import os
from obspy.core.util import _getVersionString


path = os.path.dirname(__file__)


__docformat__ = 'epytext en'
__version__ = _getVersionString("seishub.core")
__url__ = 'http://www.seishub.org/'
__copyright__ = '(C) 2007-2011 Robert Barsch & Paul Käufl'
__license__ = 'GNU Lesser General Public License, Version 3'
__license_long__ = open(os.path.join(path, "LICENSE.txt")).read()
