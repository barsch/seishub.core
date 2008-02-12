from seishub.util.text import to_unicode

str = 'Das Expos\xc3\xa9 ist d\xc3\xbcmmlicher K\xc3\xa4se'

print type(str)
print str

# the following works on my python console, but not within the script:
ustr = unicode(str,"utf-8")
print type(ustr)
print ustr

# works neither on the console nor in the script:
tustr = to_unicode(str)
print type(tustr) 
print tustr