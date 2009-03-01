# -*- coding: utf-8 -*-

import os

from zope.interface import implements
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import  sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from twisted.cred import checkers, credentials, error
from twisted.internet import defer

from seishub.util.text import hash
from seishub.exceptions import NotFoundError, DuplicateObjectError
from seishub.exceptions import SeisHubError


class PasswordDictChecker:
    """
    A simple Twisted password checker using a dictionary as input.
    """
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,)
    
    def __init__(self, env):
        self.env = env
    
    def requestAvatarId(self, credentials):
        """
        @param credentials: something which implements one of the interfaces in
        self.credentialInterfaces.
        
        @return: a Deferred which will fire a string which identifies an
        avatar, an empty tuple to specify an authenticated anonymous user
        (provided as checkers.ANONYMOUS) or fire a Failure(UnauthorizedLogin).
        Alternatively, return the result itself.
        """
        username = credentials.username
        if username in self.env.auth.passwords:
            if hash(credentials.password) == self.env.auth.passwords[username]:
                return defer.succeed(username)
        err = error.UnauthorizedLogin("No such user or bad password")
        return defer.fail(err)


UserBase = declarative_base()

class User(UserBase):
    """
    A user object.
    """
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    name = Column(String)
    password = Column(String)
    institution = Column(String)
    email = Column(String)
    
    def __init__(self, id, name, password, institution='', email=''):
        self.id = id
        self.name = name
        self.password = password
        self.institution = institution
        self.email = email
    
    def __repr__(self):
        return "<User('%s', '%s')>" % (self.id, self.name)


class AuthenticationManager(object):
    """
    The Authentication Manager.
    """
    
    passwords = {}
    users = []
    
    def __init__(self, env):
        self.env = env
        # fetch db uri - this is an option primary for the test cases
        uri = 'sqlite:///' + os.path.join(self.env.config.path, 'db', 'auth.db')
        engine = create_engine(uri, encoding = 'utf-8', convert_unicode = True)
        # Define and create user table
        metadata = UserBase.metadata
        metadata.create_all(engine, checkfirst = True)
        self.Session = sessionmaker(bind=engine)
        self.refresh()
        # add admin if no account exists and check for the default password
        if not self.users:
            self.env.log.warn("An administrative account with both username "
                              "and passwort 'admin' has been automatically "
                              "created. You should change the password as "
                              "soon as possible.")
            self.addUser('admin', 'Administrator', 'admin')
        elif self.checkPassword('admin', 'admin'):
            self.env.log.warn("The administrative account is accessible via "
                              "the standard password! Please change this as "
                              "soon as possible!")
    
    def _validatePassword(self, password):
        """
        All kind of password checks.
        """
        min_length = self.env.config.getint('webadmin', 'min_password_length')
        if len(password) < min_length:
            raise SeisHubError("Password is way to short!")
    
    def addUser(self, id, name, password, institution='', email=''):
        """
        Adds an user.
        """
        if id in self.passwords:
            raise DuplicateObjectError("User already exists!")
        self._validatePassword(password)
        user = User(id, name, hash(password), institution, email)
        session = self.Session()
        session.add(user)
        try:
            session.commit()
        except:
            session.rollback()
        self.refresh()
    
    def checkPassword(self, id, password):
        """
        Check current password.
        """
        if id not in self.passwords:
            return False
        return self.passwords[id]==hash(password)
    
    def checkPasswordHash(self, id, hash):
        """
        Check current password hash.
        """
        if id not in self.passwords:
            return False
        return self.passwords[id]==hash
    
    def changePassword(self, id, password):
        """
        Modifies only the user password.
        """
        self.updateUser(id, password=password)
    
    def updateUser(self, id, name='', password='', institution='', email=''):
        """
        Modifies user information.
        """
        if id not in self.passwords:
            raise SeisHubError("User does not exists!")
        session = self.Session()
        user = session.query(User).filter_by(id=id).one()
        if name:
            user.name = name
        if password:
            self._validatePassword(password)
            user.password = hash(password)
        if institution:
            user.institution = institution
        if email:
            user.email = email
        session.update(user)
        try:
            session.commit()
        except:
            session.rollback()
        self.refresh()
    
    def deleteUser(self, id):
        """
        Deletes a user.
        """
        if id not in self.passwords:
            raise NotFoundError("User does not exists!")
        session = self.Session()
        user = session.query(User).filter_by(id=id).one()
        session.delete(user)
        try:
            session.commit()
        except:
            session.rollback()
        self.refresh()
    
    def refresh(self):
        """
        Refreshes the internal list of users and passwords from database.
        """
        session = self.Session()
        passwords = {}
        users = []
        for user in session.query(User).order_by(User.name).all(): 
            passwords[user.id] = user.password
            users.append(user)
        self.users = users
        self.passwords = passwords
    
    def getCheckers(self):
        """
        Returns a tuple of checkers used by Twisted portal objects.
        """
        self.refresh()
        return (PasswordDictChecker(self.env),)
