#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SeisHub installer

:copyright:
    Robert Barsch (barsch@lmu.de)
    Paul Käufl (paul.kaeufl@geophysik.uni-muenchen.de)
:license:
    GNU General Public License (GPL)
    
    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
    02110-1301, USA.
"""

from setuptools import find_packages, setup
import distribute_setup
import os
distribute_setup.use_setuptools()


# check Python version
if not sys.hexversion >= 0x2060000:
    print("ERROR: SeisHub needs at least Python 2.6 or higher in " +
          "order to run.")
    exit()
if not sys.hexversion <= 0x3000000:
    print("ERROR: SeisHub is not yet compatible with Python 3.x.")
    exit()


VERSION = open(os.path.join("seishub", "VERSION.txt")).read()


setup(
    name='seishub',
    version=VERSION,
    description="SeisHub - a seismological XML/SQL database hybrid",
    long_description="""
    SeisHub - Web-based technology for storage and processing of
    multi-component data in seismology.

    For more information visit http://www.seishub.org.
    """,
    url='http://www.seishub.org',
    author='Robert Barsch',
    author_email='barsch@lmu.de',
    license='GNU General Public License (GPL)',
    platforms='OS Independent',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Physics',
    ],
    keywords=['SeisHub', 'seismology'],
    packages=find_packages(exclude=[]),
    namespace_packages=['seishub'],
    zip_safe=False,
    install_requires=[
        'Twisted',
        'Cheetah',
        'sqlalchemy',
        'PyOpenSSL',
        'lxml',
        'pycrypto',
        'pyasn1',
        'pyparsing',
        'obspy.core',
        'obspy.mseed',
        'obspy.gse2',
        'obspy.seishub',
        'obspy.imaging',
        'obspy.xseed',
        'obspy.arclink',
        'obspy.db',
    ],
    download_url="https://svn.geophysik.uni-muenchen.de/svn/seishub/trunk/seishub#egg=seishub-dev",
    include_package_data=True,
    test_suite="seishub.tests.suite",
    entry_points={
        'console_scripts': [
            'seishub-runtests = seishub.test:runtests',
            'seishub-admin = seishub.env:admin',
        ],
    },
)
