import re
import os
import string
import binascii

_re_mac = re.compile(r'([%s]{1,2}):([%s]{1,2}):([%s]{1,2}):'
                     r'([%s]{1,2}):([%s]{1,2}):([%s]{1,2})$'
                     % ((string.hexdigits,) * 6))

def parse_mac(mac):
  m = _re_mac.match(mac)
  if not m:
    raise ValueError, "Invalid mac %s" % mac

  ret = 0L
  for byte in m.groups():
    if len(byte) == 1:
      byte = "0" + byte
    val = ord(binascii.unhexlify(byte))
    ret <<= 8
    ret |= val
  return ret

def mac_str(mac):
  if mac < 0 or mac >= 1L << 48:
    raise ValueError, "Invalid mac %s" % mac
  return "%02x:%02x:%02x:%02x:%02x:%02x" % ((mac >> 40) & 255,
                                            (mac >> 32) & 255,
                                            (mac >> 24) & 255,
                                            (mac >> 16) & 255,
                                            (mac >> 8)  & 255,
                                            (mac)       & 255)

_re_ip = re.compile(r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')

def parse_ip(ip):
  m = _re_ip.match(ip)
  if not m:
    raise ValueError, "Invalid ip %s" % ip
  ret = 0L
  for byte in m.groups():
    val = int(byte)
    if val > 255:
      raise ValueError, "Invalid ip %s" % ip
    ret <<= 8
    ret |= val
  return ret

def ip_str(ip):
  if ip < 0 or ip >= 1L << 32:
    raise ValueError, "Invalid ip %s" % ip
  return "%i.%i.%i.%i" % ((ip >> 24) & 255,
                          (ip >> 16) & 255,
                          (ip >> 8)  & 255,
                          (ip)       & 255)

def ip2mac(ip):
  fp = os.popen('/sbin/ip neigh show %s' % ip_str(ip))
  try:
    out = fp.read()
  finally:
    fp.close()

  pos = out.find('lladdr ')
  if pos >= 0:
    try:
      return parse_mac(out[pos+7:pos+24])
    except ValueError:
      pass
  return None

