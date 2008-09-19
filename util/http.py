# -*- coding: utf-8 -*-

# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# see http://source.schooltool.org

def parseAccept(value):
    """Parse HTTP Accept: header.
    
    See RFC 2616, section 14.1 for a formal grammar.
    
    Returns a list of tuples
      (qvalue, media_type, media_params, accept_params)
    
    @return: qvalue is a float in range 0..1 (inclusive)
    @return: media_type is a string "type/subtype", it can be "type/*" or "*/*"
    @return: media_params is a dict
    @return: accept_params is a dict
    """
    if not value:
        return []
     
    results = []
    for media in map(str.strip, splitQuoted(value, ',')):
        if not media:
            continue
        items = splitQuoted(media, ';')
        media_type = items[0].strip()
        if not validMediaType(media_type):
            raise ValueError('Invalid media type: %s' % media_type)
        params = media_params = {}
        accept_params = {}
        q = 1.0
        for item in items[1:]:
            try:
                key, value = item.split('=', 1)
            except ValueError:
                raise ValueError('Invalid parameter: %s' % item)
            key = key.lstrip()
            value = value.rstrip()
            if not validToken(key):
                raise ValueError('Invalid parameter name: %s' % key)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            else:
                if not validToken(value):
                    raise ValueError('Invalid parameter value: %s'
                                     % value)
            if key in ('q', 'Q'):
                try:
                    q = float(value)
                except ValueError:
                    raise ValueError('Invalid qvalue: %s' % q)
                else:
                    if q < 0 or q > 1:
                        raise ValueError('Invalid qvalue: %s' % q)
                params = accept_params
            else:
                params[key] = value
        results.append((q, media_type, media_params, accept_params))
    return results


def splitQuoted(s, sep):
    """Split s using sep as the separator.
    
    Does not split when sep occurs within a quoted string.
    """
    assert len(sep) == 1
    results = []
    start = 0
    state = 0
    for i, c in enumerate(s):
        if state == 0 and c == sep:
            results.append(s[start:i])
            start = i + 1
        elif state == 0 and c == '"':
            state = 1
        elif state == 1 and c == '"':
            state = 0
        elif state == 1 and c == '\\':
            state = 2
        elif state == 2:
            state = 1
    results.append(s[start:])
    return results


def validToken(s):
    """Checks whether s is a syntactically valid token."""
    invalid_chars = list('()<>@,;:\\"/[]?={}\177') + map(chr, range(33))
    for c in s:
        if c in invalid_chars:
            return False
    return s != ''


def validMediaType(s):
    """Check whether s is a syntactically valid media type."""
    if s.count('/') != 1:
        return False
    type, subtype = s.split('/')
    if not validToken(type):
        return False
    if not validToken(subtype):
        return False
    if type == '*' and subtype != '*':
        return False
    return True


def matchMediaType(media_type, params, pattern, pattern_params):
    """Match the media type with a pattern and return the precedence level.
    
    Returns -1 if the media type does not match the pattern.
    
    >>> matchMediaType('text/css', {'level': '2'}, '*/*', {})
    1
    >>> matchMediaType('text/css', {'level': '2'}, 'text/*', {})
    2
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {})
    3
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {'level': '2'})
    4
    >>> matchMediaType('text/css', {'level': '2'}, 'text/css', {'level': '1'})
    -1
    >>> matchMediaType('text/plain', {}, '*/*', {})
    1
    >>> matchMediaType('text/plain', {}, 'text/*', {})
    2
    >>> matchMediaType('text/plain', {}, 'text/plain', {})
    4
    >>> matchMediaType('text/plain', {}, 'text/plain', {'level': '2'})
    -1
    >>> matchMediaType('text/plain', {}, 'text/html', {})
    -1
    >>> matchMediaType('text/plain', {}, 'image/png', {})
    -1
    >>> matchMediaType('text/plain', {}, 'image/*', {})
    -1
    """
    if media_type == pattern and params == pattern_params:
        return 4
    elif media_type == pattern and not pattern_params:
        return 3
    elif pattern.endswith('/*') and media_type.startswith(pattern[:-1]):
        return 2
    elif pattern == '*/*':
        return 1
    else:
        return -1


def qualityOf(media_type, params, accept_list):
    """Calculate the media quality value for a given media type.
    
    See RFC 2616 section 14.1 for details.
    
    The accept list is in the same format as returned by parseAccept.
    """
    if not accept_list:
        return 1
    best_qv = 0
    best_precedence = 0
    for qv, pattern, mparams, _ in accept_list:
        precedence = matchMediaType(media_type, params, pattern, mparams)
        if precedence > best_precedence:
            best_precedence = precedence
            best_qv = qv
    return best_qv


def chooseMediaType(supported_types, accept_list):
    """Choose the best matching media type.
    
    supported_types should be a sequence of media types.  Media type can
    be a string or a tuples of (media_type, params_dict).
    
    The accept list is in the same format as returned by parseAccept.
    
    Returns the media type that has the largest quality value as calculated
    by qualityOf.  If the largest quality value is 0, returns None.
    """
    best = None
    best_q = 0
    for choice in supported_types:
        if isinstance(choice, tuple):
            media_type, params = choice
        else:
            media_type, params = choice, {}
        q = qualityOf(media_type, params, accept_list)
        if q > best_q:
            best_q = q
            best = choice
    return best