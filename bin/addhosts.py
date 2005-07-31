#!/usr/bin/env python

import sys

from net import db, hosts, addr

def usage():
  sys.stderr.write("""\
Usage: addhosts.py
Add hosts from mysql database to iptables
""")

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      try:
        for host in hosts.get_hosts(cursor):
          print "Adding host `%s' (%s)" % (host.name, addr.mac_str(host.mac))
          host.iptables_add(cursor)
      except:
        db.log_exception(cursor, 'ADDHOSTS.PY FATAL ERROR')
        raise
    finally:
      cursor.close()
  finally:
    conn.close()

