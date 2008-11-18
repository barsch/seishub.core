# -*- coding: utf-8 -*-

import re


#def toUnicode(data, remove_decl = False):
#    """Convert a XML string to unicode by detecting the encoding and optionally
#    remove the XML declaration.
#    """
#    encoding = toUnicode(data, remove_decl)
#    data = unicode(data, encoding)
#    return data


def toUnicode(data, remove_decl = False):
    """Detect the encoding of a XML string via BOM and XML declaration.
    
    Encoding detection works as follows:
        - if detection of the BOM succeeds, the codec name of the
        corresponding unicode charset is returned
        
        - if BOM detection fails, the xml declaration is searched for
        the encoding attribute and its value returned. the "<"
        character has to be the very first in the file then (it's xml
        standard after all).
        
        - if BOM and xml declaration fail, utf-8 is returned. According
        to xml 1.0 it should be utf_8 then, but it wasn't detected by
        the means offered here. at least one can be pretty sure that a
        character coding including most of ASCII is used :-/
    """
    data, enc = detectBOM(data)
    if not enc:
        # BOM not detected, try to parse declaration:
        data, enc = parseXMLDeclaration(data, remove_decl)
    elif remove_decl:
        # BOM detected, convert to unicode and strip declaration
        data = unicode(data, enc)
        data, _ = parseXMLDeclaration(data, True)
    if not isinstance(data, unicode):
        data = unicode(data, enc)
    return data, enc

def parseXMLDeclaration(data, remove_decl = False):
    """Parse XML declaration and return (data, encoding). 
    
    If remove is True, data without the XML declaration is returned. 
    If no declaration can be found, (None, None) is returned.
    """
    
    ## set up regular expression
    xmlDeclPattern = r"""
    ^<\?xml\s+             # w/o BOM, xmldecl starts with <?xml at the first byte
        ([^>]*?                 # some chars (version info), matched minimal
    (encoding(\s*)=(\s*)           # encoding attribute begins
    ["']                # attribute start delimiter
    (?P<encstr>         # what's matched in the brackets will be named encstr
     [^"']+              # every character not delimiter (not overly exact!)
    )                   # closes the brackets pair for the named group
    ["']))?               # attribute end delimiter
    [^>]*                 # some chars optionally (standalone decl or whitespace)
    \?>                 # xmldecl end
    """
    
    xmlDeclRE = re.compile(xmlDeclPattern, re.VERBOSE)
    
#    # utf-8 encode
#    if isinstance(data, unicode):
#        #import pdb;pdb.set_trace()
#        data = data.encode("utf-8")
    # import pdb;pdb.set_trace()
    ## search and extract encoding string
    match = xmlDeclRE.search(data)
    # @see: http://www.w3.org/TR/2006/REC-xml11-20060816/#charencoding
    enc = "utf-8"
    if match:
        enc = match.group("encstr") or "utf-8"

    if remove_decl:
        data = xmlDeclRE.sub('', data)
    
    return data.strip(), enc.lower()

def detectBOM(data):
    """Attempts to detect the character encoding of the given XML string.
    
    @author: Lars Tiede
    @since: 2005/01/20
    @version: 1.1
    @see: U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/363841}
          U{http://www.w3.org/TR/2006/REC-xml-20060816/#sec-guessing}
    """
    ### detection using BOM
    
    ## the BOMs we know, by their pattern
    bomDict={ # bytepattern : name              
             (0x00, 0x00, 0xFE, 0xFF) : "utf-32be",
             (0xFF, 0xFE, 0x00, 0x00) : "utf-32le",
             (0xFE, 0xFF, None, None) : "utf-16be",
             (0xFF, 0xFE, None, None) : "utf-16le",
             (0xEF, 0xBB, 0xBF, None) : "utf-8",
            }
    ## go to beginning of file and get the first 4 bytes
    (byte1, byte2, byte3, byte4) = tuple(map(ord, data[0:4]))
    
    ## try bom detection using 4 bytes, 3 bytes, or 2 bytes and strip bom
    bomDetection = bomDict.get((byte1, byte2, byte3, byte4))
    if not bomDetection :
        bomDetection = bomDict.get((byte1, byte2, byte3, None))
        if not bomDetection :
            bomDetection = bomDict.get((byte1, byte2, None, None))
            if bomDetection:
                data = data[2:]
        else:
            data = data[3:]
    else:
        data = data[4:]
    
    ## if BOM detected, we're done :-)
    if bomDetection:
        return data, bomDetection

    ## still here? BOM detection failed.
    ##  now that BOM detection has failed we assume one byte character
    ##  encoding behaving ASCII - of course one could think of nice
    ##  algorithms further investigating on that matter, but I won't for now.

    return data, None


def addXMLDeclaration(data, encoding = "UTF-8", version = "1.0"):
    decl = '<?xml version="%s" encoding="%s"?>\n\n'
    return decl % (version, encoding) + data