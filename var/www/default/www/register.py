import re
import os

_re_ip = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
_re_mac = re.compile(r'lladdr ([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}'
                     r':[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})')

def index(req, url=None):
  ip = req.connection.remote_ip

  if not _re_ip.match(ip):
    raise "Invalid ip '%s'" % ip

  fp = os.popen('/sbin/ip neigh show %s' % ip)
  try:
    out = fp.read()
  finally:
    fp.close()

  match = out and _re_mac.search(out)
  if not match:
    raise "Could not determine MAC address for %s" % ip

  mac = match.group(1)
  
  return "url=%s\nip=%s\nmac=%s" % (url, ip, mac)
