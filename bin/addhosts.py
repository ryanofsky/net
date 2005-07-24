#!/usr/bin/env python

import sys
from net.db import connect, get_hosts, REGISTERED, BLOCKED
from net.iptables import add_registered, add_blocked
from net.addr import mac_str

def addhosts():
  db = connect()
  try:
    cursor = db.cursor()
    try:
      for name, ip, mac in get_hosts(cursor, REGISTERED):
        print "Registering %s (%s)" % (name, mac_str(mac))
	add_registered(ip, mac)
      for name, ip, mac in get_hosts(cursor, BLOCKED):
        print "Blocking %s (%s)" % (name, mac_str(mac))
	add_blocked(mac)
    finally:
      cursor.close()
  finally:
    db.close()
  
def usage():
  sys.stderr.write("""\
Usage: addhosts.py
Add hosts from mysql database to iptables
""")

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  addhosts()
