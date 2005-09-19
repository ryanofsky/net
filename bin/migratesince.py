#!/usr/bin/env python

from net import db, hosts, addr
import sys, re

db.DEBUG = True

def usage():
  sys.stderr.write("""\
Usage: migratesince.py
Add registered_since column to hosts table
""")

def add_since(conn):
  cursor = conn.cursor()
  cursor.execute("ALTER TABLE hosts "
                 "ADD COLUMN since DATETIME NOT NULL AFTER blocked")

def set_since(conn):
  cursor = conn.cursor()
  upcursor = conn.cursor()

  cursor.execute("SELECT time, message FROM log ORDER BY message_id")
  while True:
    row = cursor.fetchone()
    if not row:
      break

    time, message = row
    mac = parse_add_host(message)
    if mac is not None:
      time = db.parse_time(time)
      upcursor.execute("UPDATE hosts SET since = %s "
                       "WHERE mac_addr = %s", (db.time_str(time), mac))
      print ("Setting time '%s' for mac '%s' (%i rows)" 
             % (db.time_str(time), addr.mac_str(mac), upcursor.rowcount))
      
_re_add_host = re.compile(r'^Adding host: mac = ([^,]+)')

def parse_add_host(message):
  m = _re_add_host.match(message)
  if m is not None:
    print m.groups()
    return addr.parse_mac(m.group(1))

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  conn = db.connect()
  add_since(conn)
  set_since(conn)

