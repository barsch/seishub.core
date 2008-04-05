# -*- coding: utf-8 -*-

from twisted.cred import portal, checkers, credentials, error as credError
from twisted.internet import defer

from zope.interface import Interface, implements


class INamedUserAvatar(Interface):
    """Should have attributes username and fullname."""


class NamedUserAvatar(object):
    implements(INamedUserAvatar)
    
    def __init__(self, username, fullname):
        self.username = username
        self.fullname = fullname


class PasswordDictChecker(object):
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)
    
    def __init__(self, passwords):
        self.passwords = passwords
    
    def requestAvatarId(self, credentials):
        username = credentials.username
        if self.passwords.has_key(username):
            if credentials.password == self.passwords[username]:
                return defer.succeed(username)
            else:
                return defer.fail(credError.UnauthorizedLogin("Bad password"))
        else:
            return defer.fail(credError.UnauthorizedLogin("No such user"))

class SeisHubRealm(object):
    implements(portal.IRealm)
    
    def __init__(self, users):
        self.users = users
    
    def requestAvatar(self, avatarId, mind, *interfaces):
        if INamedUserAvatar in interfaces:
            fullname = self.users[avatarId]
            logout = lambda: None
            return (INamedUserAvatar, NamedUserAvatar(avatarId, fullname), 
                    logout)
        else:
            raise KeyError("None of the requested Interfaces is supported.")


users = {'admin': 'Administrator', 'barsch': 'Robert Barsch'}
passwords = {'admin': 'aaa', 'barsch': 'muh'}

class Portal(portal.Portal):
    def __init__(self):
        realm = SeisHubRealm(users)
        checkers = (PasswordDictChecker(passwords),)
        portal.Portal.__init__(self, realm, checkers)
