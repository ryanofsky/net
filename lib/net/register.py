from mod_python import apache, util
import urllib

def handler(req):
  req.content_type = 'text/plain'
  try:
    host = req.headers_in['Host']
  except KeyError:
    url = ''
  else:
    url = 'http://%s%s' % (host, req.unparsed_uri)

  util.redirect(req, 'http://kalam/register.py'
                + (url and '?url=' + urllib.quote(url, ':/')))
  return apache.OK
