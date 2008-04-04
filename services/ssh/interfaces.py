# -*- coding: utf-8 -*-

from seishub.core import Interface


class ISSHCommand(Interface):
    """Extension point interface for adding commands to the SSH service."""

    def getCommandId(self):
        """Return a command string."""

    def executeCommand(self, args):
        """
        Process a command line given as an arrays of arguments and 
        returns a list of strings.
        """
