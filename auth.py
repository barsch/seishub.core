# -*- coding: utf-8 -*-

from seishub.config import IntOption
from seishub.defaults import MIN_PASSWORD_LENGTH
from seishub.exceptions import NotFoundError, DuplicateObjectError, \
    SeisHubError
from seishub.util.text import hash
from sqlalchemy import Column, String, create_engine, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from twisted.cred import checkers, credentials, error
from twisted.internet import defer
from zope.interface import implements
import os


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


Base = declarative_base()

class User(Base):
    """
    A user object.
    """
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    uid = Column(Integer)
    name = Column(String)
    password = Column(String)
    institution = Column(String)
    email = Column(String)

    def __init__(self, id, name, password, uid=1000, institution='', email=''):
        self.id = id
        self.uid = uid
        self.name = name
        self.password = password
        self.institution = institution
        self.email = email

    def __repr__(self):
        return "<User %s(%d): '%s')>" % (self.id, self.uid, self.name)


class Guppy(Base):
    """
    A guppy object.
    """
    __tablename__ = 'guppy'

    timestamp = Column(DateTime, primary_key=True)
    size = Column(Integer)
    count = Column(Integer)

    def __init__(self, timestamp, size, count):
        self.timestamp = timestamp
        self.size = size
        self.count = count


class AuthenticationManager(object):
    """
    The Authentication Manager.
    """
    IntOption('seishub', 'min_password_length', MIN_PASSWORD_LENGTH,
        "Minimum password length.")

    passwords = {}
    users = []

    def __init__(self, env):
        self.env = env
        # fetch db uri - this is an option primary for the test cases
        uri = 'sqlite:///' + os.path.join(self.env.config.path, 'db',
                                          'auth.db')
        engine = create_engine(uri, encoding='utf-8', convert_unicode=True)
        # Define and create user table
        metadata = Base.metadata
        metadata.create_all(engine, checkfirst=True)
        self.Session = sessionmaker(bind=engine)
        self.refresh()
        # add admin if no account exists and check for the default password
        if not self.users:
            self.env.log.warn("An administrative account with both username "
                              "and passwort 'admin' has been automatically "
                              "created. You should change the password as "
                              "soon as possible.")
            self.addUser(id='admin', name='Administrator', password='admin',
                         uid=100, checkPassword=False)
        elif self.checkPassword('admin', 'admin'):
            self.env.log.warn("The administrative account is accessible via "
                              "the standard password! Please change this as "
                              "soon as possible!")
        # clear guppy table at start-up
        self.clearGuppy()

    def _validatePassword(self, password):
        """
        All kind of password checks.
        """
        min_length = self.env.config.getint('seishub', 'min_password_length')
        if len(password) < min_length:
            raise SeisHubError("Password is way to short!")

    def addUser(self, id, name, password, uid=1000, institution='', email='',
                checkPassword=True):
        """
        Adds an user.
        """
        if id in self.passwords:
            raise DuplicateObjectError("User already exists!")
        if checkPassword:
            self._validatePassword(password)
        user = User(id=id, uid=uid, name=name, password=hash(password),
                    institution=institution, email=email)
        session = self.Session()
        session.add(user)
        try:
            session.commit()
        except Exception, e:
            session.rollback()
            raise SeisHubError(str(e))
        self.refresh()

    def checkPassword(self, id, password):
        """
        Check current password.
        """
        if id not in self.passwords:
            raise SeisHubError("User does not exists!")
        return self.passwords[id] == hash(password)

    def checkPasswordHash(self, id, hash):
        """
        Check current password hash.
        """
        if id not in self.passwords:
            raise SeisHubError("User does not exists!")
        return self.passwords[id] == hash

    def changePassword(self, id, password):
        """
        Modifies only the user password.
        """
        self.updateUser(id, password=password)

    def getUser(self, id):
        if id not in self.passwords:
            raise SeisHubError("User does not exists!")
        session = self.Session()
        user = session.query(User).filter_by(id=id).one()
        try:
            session.commit()
        except:
            session.rollback()
        return user

    def updateUser(self, id, name='', password='', uid=1000, institution='',
                   email=''):
        """
        Modifies user information.
        """
        if id not in self.passwords:
            raise SeisHubError("User does not exists!")
        session = self.Session()
        user = session.query(User).filter_by(id=id).one()
        user.name = name
        if password:
            self._validatePassword(password)
            user.password = hash(password)
        user.institution = institution
        user.email = email
        user.uid = uid
        session.add(user)
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

#XXX: should go out of auth - needs refactoring!

    def addGuppy(self, timestamp, size, count):
        """
        Adds a guppy entry.
        """
        guppy = Guppy(timestamp=timestamp, size=size, count=count)
        session = self.Session()
        session.add(guppy)
        try:
            session.commit()
        except Exception, e:
            session.rollback()
            raise SeisHubError(str(e))

    def getGuppy(self, number=10):
        session = self.Session()
        guppy = session.query(Guppy).order_by(Guppy.timestamp).limit(number)
        try:
            session.commit()
        except:
            session.rollback()
        return guppy

    def clearGuppy(self):
        session = self.Session()
        session.query(Guppy).delete()
        try:
            session.commit()
        except:
            session.rollback()
