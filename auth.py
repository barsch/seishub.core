# -*- coding: utf-8 -*-

from twisted.cred import checkers, credentials, error
from twisted.internet import defer
from zope.interface import implements


class PasswordDictChecker:
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)
    
    def __init__(self, passwords):
        self.passwords = passwords
    
    def requestAvatarId(self, credentials):
        username = credentials.username
        if self.passwords.has_key(username):
            if credentials.password == self.passwords[username]:
                return defer.succeed(username)
        err = error.UnauthorizedLogin("No such user or bad password")
        return defer.fail(err)


def UserManager(env):
    users = {'admin': 'aaa', 'barsch': 'muh'}
    return (PasswordDictChecker(users),)
