#!/usr/bin/env python

DEBUG = False

import sys
from net import db, iptables, addr, hosts

def error(cursor, str):
  if DEBUG:
    print str
    print
  else:
    db.log(cursor, "addcounts.py error: %s" % str)

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
                        "%s (rule = %s)"
                        % (chain, db.log_str(fields['destination']), fields))
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
                        "%s (rule = %s)"
                        % (chain, db.log_str(fields['source']), fields))
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
          error(cursor, "Rule in chain %s has invalid MAC %s "
                        "(ip = %s, rule = %s)"
                        % (chain, db.log_str(mac[4:]), addr.ip_str(ip), fields))
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
    host = hosts.lookup_ip(cursor, ip)
    if not host:
      error(cursor, "Unknown ip %s encountered in filter table "
                    "(MAC = %s, in_bytes = %s, out_bytes = %s)"
                    % (addr.ip_str(ip), mac and addr.mac_str(mac),
                       in_bytes, out_bytes))
      continue

    if mac is not None and host.mac != mac:
      error(cursor, "Wrong MAC address in filter table for IP %s "
                    "(expected MAC = %s, MAC = %s, in_bytes = %s, "
                    "out_bytes = %s)"
                        % (addr.ip_str(ip), addr.mac_str(host.mac),
                           addr.mac_str(mac), in_bytes, out_bytes))
      continue

    db.add_count(cursor, host.id, in_bytes, out_bytes)

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
        if not DEBUG:
          db.log_exception(cursor, 'ADDCOUNTS.PY FATAL ERROR')
        raise
    finally:
      cursor.close()
  finally:
    conn.close()

