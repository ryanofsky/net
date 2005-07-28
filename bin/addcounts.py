#!/usr/bin/env python

DEBUG = False

import sys
import traceback
import cStringIO

from net import db, iptables, addr

def error(cursor, str):
  if DEBUG:
    print str
    print
  else:
    db.log(cursor, "addcounts.py error: %s" % str)

def exception_str():
  fp = cStringIO.StringIO()
  traceback.print_exc(None, fp)
  return fp.getvalue()

def merge_counts(cursor, incoming, outgoing):
  for ip, (out_bytes, mac) in outgoing.items():
    try:
      in_bytes = incoming[ip]
    except KeyError:
      error(cursor, "Could not determine incoming bytes for ip %s"
                     % addr.ip_str(ip))
      yield ip, mac, None, out_bytes
    else:
      del incoming[ip]
      yield ip, mac, in_bytes, out_bytes
  for ip, in_bytes in incoming.items():
    error(cursor, "Could not determine outgoing bytes for ip %s"
                   % addr.ip_str(ip))
    yield ip, None, in_bytes, None

def add_counts(cursor):
  counts = iptables.open_counts(zero=True)
  try:
    # dictionary of incoming byte counts indexed by ip
    incoming = {}

    # dictionary of (outgoing byte counts, mac addresses) indexed by ip
    outgoing = {}

    for chain, fields in iptables.read_counts(counts):
      if chain == 'ACCEPT_REGISTERED_DST':
        try:
          ip = addr.parse_ip(fields['destination'])
        except ValueError:
          error(cursor, "Rule in chain %s has invalid destination ip "
                        "`%s' (rule = %s)" 
                        % (chain, fields['destination'], fields))
          continue

        if incoming.has_key(ip):
          error(cursor, "Duplicate rule in chain %s for single ip "
                        "(ip = %s, rule = %s)"
                        % (chain, addr.ip_str(ip), fields))
          continue

        incoming[ip] = int(fields['bytes'])

      elif chain == 'ACCEPT_REGISTERED_SRC':
        try:
          ip = addr.parse_ip(fields['source'])
        except ValueError:
          error(cursor, "Rule in chain %s has invalid source ip "
                        "`%s' (rule = %s)" 
                        % (chain, fields['source'], fields))
          continue

        mac = fields['extra']
        if mac[:4] != 'MAC ':
          error(cursor, "Rule in chain %s doesn't specify MAC "
                        "(ip = %s, rule = %s)"
                        % (chain, addr.ip_str(ip), fields))
          continue
        try:
          mac = addr.parse_mac(mac[4:])
        except ValueError:
          error(cursor, "Rule in chain %s has invalid MAC `%s' "
                        "(ip = %s, rule = %s)"
                        % (chain, mac[4:], addr.ip_str(ip), fields))
          continue
                
        if outgoing.has_key(ip):
          error(cursor, "Duplicate rule in chain %s for single ip "
                        "(ip = %s, rule = %s)"
                        % (chain, addr.ip_str(ip), fields))
          continue

        outgoing[ip] = int(fields['bytes']), mac

  finally:
    iptables.close_counts(counts)

  for ip, mac, in_bytes, out_bytes in merge_counts(cursor, incoming, 
                                                   outgoing):
    cursor.execute("SELECT host_id, mac_addr FROM hosts "
                   "WHERE ip_addr = %s", ip)
 
    row = cursor.fetchone()
    if not row:
      error(cursor, "Unknown ip %s encountered in filter table "
                    "(MAC = %s, in_bytes = %s, out_bytes = %s)"
                    % (addr.ip_str(ip), mac and addr.mac_str(mac), 
                       in_bytes, out_bytes))
      continue
 
    # just assume this database constraint holds
    assert cursor.rowcount == 1
 
    host_id, reg_mac = row
    if mac is not None and reg_mac != mac:
      error(cursor, "Wrong MAC address in filter table for IP %s "
                    "(expected MAC = %s, MAC = %s, in_bytes = %s, "
                    "out_bytes = %s)"
                        % (addr.ip_str(ip), addr.mac_str(reg_mac), 
                           addr.mac_str(mac), in_bytes, out_bytes))
      continue

    db.add_count(cursor, host_id, in_bytes, out_bytes)
  
def usage():
  sys.stderr.write("""\
Usage: addcounts.py
Add byte counts from iptables to mysql database
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
        add_counts(cursor)
      except:
        error(cursor, "FATAL ERROR\n%s" % exception_str())
    finally:
      cursor.close()
  finally:
    conn.close()

