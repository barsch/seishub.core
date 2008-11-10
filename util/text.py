# -*- coding: utf-8 -*-

import locale
import re
import hashlib


def isInteger(data):
    """Tests if the given string is an integer."""
    try:
        stripped = str(int(data))
    except:
        return False
    if data == stripped:
        return True
    return False


def getFirstSentence(text, maxlen=255):
    """Returns the text left of the first occurring dot and reduces the final 
    text to maxlen chars.
    """
    if not text:
        return ""
    if "." not in text:
        return text[0:maxlen]
    text = text.split(".")
    text = text[0] + '.'
    return text[0:maxlen]


def toUnicode(text, charset=None):
    """Convert a `str` object to an `unicode` object.

    If `charset` is given, we simply assume that encoding for the text,
    but we'll use the "replace" mode so that the decoding will always
    succeed.
    If `charset` is ''not'' specified, we'll make some guesses, first
    trying the UTF-8 encoding, then trying the locale preferred encoding,
    in "replace" mode. This differs from the `unicode` builtin, which
    by default uses the locale preferred encoding, in 'strict' mode,
    and is therefore prompt to raise `UnicodeDecodeError`s.

    Because of the "replace" mode, the original content might be altered.
    If this is not what is wanted, one could map the original byte content
    by using an encoding which maps each byte of the input to an unicode
    character, e.g. by doing `unicode(text, 'iso-8859-1')`.
    """
    if not isinstance(text, str):
        if isinstance(text, Exception):
            # two possibilities for storing unicode strings in exception data:
            try:
                # custom __str__ method on the exception (e.g. PermissionError)
                return unicode(text)
            except UnicodeError:
                # unicode arguments given to the exception (e.g. parse_date)
                return ' '.join([toUnicode(arg) for arg in text.args])
        return unicode(text)
    if charset:
        return unicode(text, charset, 'replace')
    else:
        try:
            return unicode(text, 'utf-8')
        except UnicodeError:
            return unicode(text, locale.getpreferredencoding(), 'replace')


def hash(text):
    """Returns a hash of the given string."""
    return hashlib.sha224(text).hexdigest()


def validate_id(str):
    """ids have to be alphanumeric, start with a character"""
    id_pt = """^[A-Za-z0-9]       # leading character
    [A-Za-z0-9_.-]*$              # alphanumeric or '_','.','-'
    """
    # XXX: not here!
    if str is None:
        return None
    # ecnode to bytestring first
    str = str.encode("utf-8")
    # match regex
    re_id = re.compile(id_pt, re.VERBOSE)
    m = re_id.match(str)
    if not m:
        raise ValueError('Invalid id: %s' % str)
    return str


def to_uri(package_id, resourcetype_id):
    uri = '/' + package_id
    if resourcetype_id:
        uri += '/' + resourcetype_id
    return uri


def from_uri(uri):
    elements = uri.split('/')
    pid = elements[1]
    if len(elements) == 3: #no resourcetype
        rid = None
        args = elements[2]
    else:
        rid = elements[2]
        args = elements[3]
    return pid, rid, args


def to_xpath_query(package_id, resourcetype_id, expr):
    package_id = package_id or '*'
    resourcetype_id = resourcetype_id or '*'
    return '/' + package_id + '/' + resourcetype_id + expr
