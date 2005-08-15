from mod_python import apache, util

import urllib
import rfc822

def handler(req):
  try:
    host = req.headers_in['Host']
  except KeyError:
    url = ''
  else:
    url = 'http://%s%s' % (host, req.unparsed_uri)

  loc = 'http://kalam/register.py' + (url and '?url=' + urllib.quote(url, ':/'))
  date = rfc822.formatdate()

  req.status = apache.HTTP_MOVED_TEMPORARILY
  req.headers_out['Location'] = loc
  #req.headers_out['Refresh'] = '0; %s' % loc
  req.headers_out['Cache-Control'] = 'no-store, no-cache'
  req.headers_out['Pragma'] = 'no-cache'
  req.headers_out['Last-Modified'] = date
  req.headers_out['Expires'] = rfc822.formatdate(0)
  req.headers_out['Date'] = date
  req.content_type = 'text/html'
  req.write('<p>The document has moved <a href="%s">here</a></p>\n' % loc)

  return apache.OK
