#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from seishub.core.daemon import createApplication


USAGE = """
Usage: seishub-admin initenv /path/to/new/instance
"""


def main():
    """
    SeisHub administration script.
    """
    args = sys.argv
    if len(args) == 3:
        if args[1] == 'initenv':
            print('Initializing new SeisHub environment')
            path = os.path.abspath(args[2])
            if os.path.isdir(path):
                print('Error: path %s already exists!' % path)
            else:
                createApplication(path, create=True)
    else:
        print USAGE
