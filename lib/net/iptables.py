import os
import re

import db
import addr

def add_registered(cursor, ip, mac):
  run(cursor, APPEND, 'filter', 'ACCEPT_REGISTERED_SRC', 'ACCEPT', SOURCE, ip, mac)
  run(cursor, APPEND, 'filter', 'ACCEPT_REGISTERED_DST', 'ACCEPT', DEST, ip, None)
  run(cursor, APPEND, 'nat', 'ACCEPT_REGISTERED', 'ACCEPT', SOURCE, ip, mac)

def del_registered(cursor, ip, mac):
  run(cursor, DELETE, 'filter', 'ACCEPT_REGISTERED_SRC', 'ACCEPT', SOURCE, ip, mac)
  run(cursor, DELETE, 'filter', 'ACCEPT_REGISTERED_DST', 'ACCEPT', DEST, ip, None)
  run(cursor, DELETE, 'nat', 'ACCEPT_REGISTERED', 'ACCEPT', SOURCE, ip, mac)

def add_blocked(cursor, mac):
  run(cursor, APPEND, 'nat', 'REDIRECT_BLOCKED', 'BLOCK', SOURCE, None, mac)

def del_blocked(cursor, mac):
  run(cursor, DELETE, 'nat', 'REDIRECT_BLOCKED', 'BLOCK', SOURCE, None, mac)

def enable_blackout(cursor):
  run(cursor, APPEND, 'nat', 'MAYBE_BLACKOUT', 'BLOCK', SOURCE, None, None)
  run(cursor, APPEND, 'filter', 'MAYBE_BLACKOUT', 'DROP', SOURCE, None, None)

def disable_blackout(cursor):
  run(cursor, DELETE, 'nat', 'MAYBE_BLACKOUT', 'BLOCK', SOURCE, None, None)
  run(cursor, DELETE, 'filter', 'MAYBE_BLACKOUT', 'DROP', SOURCE, None, None)

APPEND = 'append'
DELETE = 'delete'

SOURCE = 'src'
DEST = 'dst'

def run(cursor, edit, table, chain, action, srcdst, ip, mac):
  ip_str = ip is None and 'none' or addr.ip_str(ip)
  mac_str = mac is None and 'none' or addr.mac_str(mac)
  cmd = ('/sbin/iptables-wrapper %s %s %s %s %s %s %s'
         % (edit, table, chain, action, srcdst, ip_str, mac_str))
  if os.system(cmd):
    db.log(cursor, "iptables error: nonzero return from %s" % db.log_str(cmd))

_re_chain = re.compile(r'^Chain (.*) \((.*)\)$')
_re_header = re.compile(r'\s*pkts\s+bytes\s+target\s+prot\s+opt\s+'
                        r'in\s+out\s+source\s+destination\s*$')
_re_entry = re.compile(r'^\s*'
                       r'(?P<pkts>\d+)\s+'
                       r'(?P<bytes>\d+)\s+'
                       r'(?P<target>\S+)\s+'
                       r'(?P<prot>\S+)\s+'
                       r'(?P<opt>\S+)\s+'
                       r'(?P<in>\S+)\s+'
                       r'(?P<out>\S+)\s+'
                       r'(?P<source>\S+)\s+'
                       r'(?P<destination>\S+)\s*'
                       r'(?P<extra>.*\S)?\s*$')

_re_zero = re.compile(r"^Zeroing chain `(.*)'$")

class ParseError(Exception):
  def __init__(self, error, line_no, line):
    Exception.__init__(self)
    self.error = error
    self.line_no = line_no
    self.line = line

  def __str__(self):
    return "Parse error: %s Line %i `%s'" % (self.error, self.line_no, self.line)

def open_counts(zero):
  return os.popen('/sbin/iptables-wrapper %s filter' % (zero and 'zero' or 'show'))

def read_counts(fp):
  line_no = 0
  while True:
    line_no += 1
    line = fp.readline()
    if not line:
      return
    if _re_zero.match(line):
      continue
    m = _re_chain.match(line)
    if not m:
      raise ParseError("could not parse chain header", line_no, line)
    chain = m.group(1)

    line_no += 1
    line = fp.readline()
    m = line and _re_header.match(line)
    if not m:
      raise ParseError("could not parse table header", line_no, line)

    while True:
      line_no += 1
      line = fp.readline()
      if not line:
        return
      if line == '\n':
        break
      if _re_zero.match(line):
        break
      m = _re_entry.match(line)
      if not m:
        raise ParseError("could not parse rule", line_no, line)
      yield chain, m.groupdict()

def close_counts(fp):
  fp.close()

