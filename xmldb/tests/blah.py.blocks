from seishub.util.text import to_unicode

str = 'Das Expos\xc3\xa9 ist d\xc3\xbcmmlicher K\xc3\xa4se'

print str
print str.__repr__()
print type(str)
print "\n"

dstr = str.decode("utf-8")
print dstr.encode("utf-8")
print dstr.__repr__()
print type(dstr)
print "\n"

ustr = unicode(str,"utf-8")
print ustr.encode("utf-8")
print ustr.__repr__()
print type(ustr)
print "\n"

tustr = to_unicode(str) 
print tustr.encode("utf-8")
print tustr.__repr__()
print type(tustr)
print "\n"

print type(tustr.encode("utf-8"))
print "\n"

# the following works on my python console, but not within the script:
ustr = unicode(str,"utf-8")
print ustr
print type(ustr)
print "\n"

tustr = to_unicode(str)
print type(tustr) 
print tustr
print "\n"