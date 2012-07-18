#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
SeisHub installer

:copyright:
    Robert Barsch (barsch@lmu.de)
    Paul Käufl (paul.kaeufl@geophysik.uni-muenchen.de)
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""

from setuptools import find_packages, setup
import os
import sys

# check Python version
if not sys.hexversion >= 0x2060000:
    print("ERROR: SeisHub needs at least Python 2.6 or higher in " +
          "order to run.")
    exit()
if not sys.hexversion <= 0x3000000:
    print("ERROR: SeisHub is not yet compatible with Python 3.x.")
    exit()


VERSION = open(os.path.join("seishub", "core", "VERSION.txt")).read()


setup(
    name='seishub.core',
    version=VERSION,
    description="SeisHub - a seismological XML/SQL database hybrid",
    long_description="""
    seishub - Web-based technology for storage and processing of
    multi-component data in seismology.

    For more information visit http://www.seishub.org.
    """,
    url='http://www.seishub.org',
    author='Robert Barsch',
    author_email='barsch@lmu.de',
    license='GNU Lesser General Public License, Version 3 (LGPLv3)',
    platforms='OS Independent',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ' + \
        'GNU Library or Lesser General Public License (LGPL)',
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
        'setuptools',
        'Twisted',
        'Cheetah',
        'sqlalchemy>0.7.7',
        'PyOpenSSL',
        'lxml',
        'pycrypto',
        'pyasn1',
        'pyparsing',
        'obspy.core>0.7.0',
    ],
    download_url="https://github.com/barsch/seishub.core/zipball/master" + \
        "#egg=seishub.core-dev",
    test_suite="seishub.core.test.suite",
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'seishub-runtests = seishub.core.scripts.runtests:main',
            'seishub-admin = seishub.core.scripts.admin:main',
        ],
    },
)
