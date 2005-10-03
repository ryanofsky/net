#!/usr/bin/env python

from net import hosts, db, addr
import sys
import time
import re

DAT = '/var/arpwatch/eth1.dat'

_re_line = re.compile(r'^(\S+)\s+(\S+)\s+(\S+)\s*$')

def macs(cursor, filename):
  fp = open(filename, 'rt')
  line_no = 1
  try:
    while True:
      line = fp.readline()
      if not line:
        break
      m = _re_line.match(line)
      if m:
        mac_str, ip_str, time_str = m.groups()
        try:
          mac = addr.parse_mac(mac_str)
        except ValueError:
          print "Invalid mac %s at %s:%i" % (mac_str, filename, line_no)
          continue

        try:
          ip = addr.parse_ip(ip_str)
        except ValueError:
          print "Invalid ip %s at %s:%i "% (ip_str, filename, line_no)
          continue

        try:
          timestamp = time.localtime(int(time_str))
        except ValueError:
          print "Invalid timestamp %s at %s:%i "% (time_str, filename, line_no)
          continue

        host = hosts.lookup_mac(cursor, mac)
        print ("%s %-15s %-15s %s" 
               % (addr.mac_str(mac), addr.ip_str(ip),
                  host and host.name or '<unknown>',
                  time.strftime('%a %b %d %H:%M:%S %Z %Y', timestamp)))
          
      else:
        print "Parse error at %s:%i" % (filename, line_no)
      line_no += 1
  finally:
    fp.close()
    
if __name__ == '__main__':
  if len(sys.argv) == 1:
    conn = db.connect()
    try:
      cursor = conn.cursor()
      try:
        macs(cursor, DAT)
      finally:
        cursor.close()
    finally:
      conn.close()
    
  else:
    print "Usage: macs.py"
    print "Print information about mac addresses currently in use on network"
    sys.exit(1)
   
