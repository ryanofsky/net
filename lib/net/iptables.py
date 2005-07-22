import os
import net.db
import net.addr

def add_registered(ip, mac):
  run(APPEND, 'filter', 'ACCEPT_REGISTERED_SRC', 'ACCEPT', SOURCE, ip, mac)
  run(APPEND, 'filter', 'ACCEPT_REGISTERED_DST', 'ACCEPT', DEST, ip, None)
  run(APPEND, 'nat', 'ACCEPT_REGISTERED', 'ACCEPT', SOURCE, ip, mac)

def del_registered(ip, mac):
  run(DELETE, 'filter', 'ACCEPT_REGISTERED_SRC', 'ACCEPT', SOURCE, ip, mac)
  run(DELETE, 'filter', 'ACCEPT_REGISTERED_DST', 'ACCEPT', DEST, ip, None)
  run(DELETE, 'nat', 'ACCEPT_REGISTERED', 'ACCEPT', SOURCE, ip, mac)

def add_blocked(mac):
  run(APPEND, 'nat', 'REDIRECT_BLOCKED', 'BLOCK', SOURCE, None, mac)

def del_blocked(mac):
  run(DELETE, 'nat', 'REDIRECT_BLOCKED', 'BLOCK', SOURCE, None, mac)

APPEND = 'append'
DELETE = 'delete'

SOURCE = 'src'
DEST = 'dst'

def run(edit, table, chain, action, srcdst, ip, mac):
  ip_str = ip is None and 'none' or net.addr.ip_str(ip)
  mac_str = mac is None and 'none' or net.addr.mac_str(mac)
  cmd = ('/sbin/iptables-wrapper %s %s %s %s %s %s %s'
         % (edit, table, chain, action, srcdst, ip_str, mac_str))
  if os.system(cmd):
    db = net.db.connect()
    try:
      net.db.log(db, "Error running `%s'" % cmd)
    finally:
      db.close()
