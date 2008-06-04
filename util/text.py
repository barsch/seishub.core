# -*- coding: utf-8 -*-

import locale


CRLF = '\r\n'


def isInteger(source):
    try:
        stripped = str(int(source))
    except:
        return False
    if source == stripped:
        return True
    return False


def to_unicode(text, charset=None):
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
                return ' '.join([to_unicode(arg) for arg in text.args])
        return unicode(text)
    if charset:
        return unicode(text, charset, 'replace')
    else:
        try:
            return unicode(text, 'utf-8')
        except UnicodeError:
            return unicode(text, locale.getpreferredencoding(), 'replace')


def detectXMLEncoding(filename):
    """Attempts to detect the character encoding of the xml file
    given by a filename.
    
    The return value can be:
        - if detection of the BOM succeeds, the codec name of the
        corresponding unicode charset is returned
        
        - if BOM detection fails, the xml declaration is searched for
        the encoding attribute and its value returned. the "<"
        character has to be the very first in the file then (it's xml
        standard after all).
        
        - if BOM and xml declaration fail, None is returned. According
        to xml 1.0 it should be utf_8 then, but it wasn't detected by
        the means offered here. at least one can be pretty sure that a
        character coding including most of ASCII is used :-/
    
    @author: Lars Tiede
    @since: 2005/01/20
    @version: 1.1
    @see: U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/363841}
          U{http://www.w3.org/TR/2006/REC-xml-20060816/#sec-guessing}
    """
    ### detection using BOM
    
    ## the BOMs we know, by their pattern
    bomDict={ # bytepattern : name              
             (0x00, 0x00, 0xFE, 0xFF) : "utf_32_be",
             (0xFF, 0xFE, 0x00, 0x00) : "utf_32_le",
             (0xFE, 0xFF, None, None) : "utf_16_be",
             (0xFF, 0xFE, None, None) : "utf_16_le",
             (0xEF, 0xBB, 0xBF, None) : "utf_8",
            }
    ## go to beginning of file and get the first 4 bytes
    try:
        fp = open(filename, 'r')
        (byte1, byte2, byte3, byte4) = tuple(map(ord, fp.read(4)))
    except:
        return None
    
    ## try bom detection using 4 bytes, 3 bytes, or 2 bytes
    bomDetection = bomDict.get((byte1, byte2, byte3, byte4))
    if not bomDetection :
        bomDetection = bomDict.get((byte1, byte2, byte3, None))
        if not bomDetection :
            bomDetection = bomDict.get((byte1, byte2, None, None))
    
    ## if BOM detected, we're done :-)
    if bomDetection :
        return bomDetection
    
    
    ## still here? BOM detection failed.
    ##  now that BOM detection has failed we assume one byte character
    ##  encoding behaving ASCII - of course one could think of nice
    ##  algorithms further investigating on that matter, but I won't for now.
    
    
    ### search xml declaration for encoding attribute
    import re
    
    ## assume xml declaration fits into the first 2 KB (*cough*)
    fp.seek(0)
    buffer = fp.read(2048)
    
    ## set up regular expression
    xmlDeclPattern = r"""
    ^<\?xml             # w/o BOM, xmldecl starts with <?xml at the first byte
    .+?                 # some chars (version info), matched minimal
    encoding=           # encoding attribute begins
    ["']                # attribute start delimiter
    (?P<encstr>         # what's matched in the brackets will be named encstr
     [^"']+              # every character not delimiter (not overly exact!)
    )                   # closes the brackets pair for the named group
    ["']                # attribute end delimiter
    .*?                 # some chars optionally (standalone decl or whitespace)
    \?>                 # xmldecl end
    """
    
    xmlDeclRE = re.compile(xmlDeclPattern, re.VERBOSE)
    
    ## search and extract encoding string
    match = xmlDeclRE.search(buffer)
    fp.close()
    if match :
        return match.group("encstr")
    else :
        return None
    
def encode_name(str):
    """Encode plain names (such as ids) to python bytestrings"""
    try:
        return str.encode("utf-8")
    except AttributeError:
        return str
