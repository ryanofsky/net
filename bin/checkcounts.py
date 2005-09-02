#!/usr/bin/env python

import sys

from net import db, hosts, addr

def usage():
  sys.stderr.write("""\
Usage: checkcounts.py
Check integrity of byte_counts table
""")

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  conn = db.connect()
  try:
    cursor = conn.cursor()
    last_host_id = None
    try:
      cursor.execute("SELECT interval_id, end_time FROM byte_count_intervals "
                     "ORDER BY interval_id")
      last = None
      while True:
        row = cursor.fetchone()
        if not row:
          break
        interval_id, end_time = row
        end = db.parse_time(end_time)
        if end is not None and last >= end:
          print ("ERROR interval %i '%s' precedes last '%s'"
                 % (interval_id, db.time_str(end), db.time_str(last)))
        last = end

      cursor.execute("SELECT byte_count_id FROM byte_counts "
                     "WHERE interval_id IS NULL")
      while True:
        row = cursor.fetchone()
        if not row:
          break
        byte_count_id, = row
        print "ERROR row %i has NULL interval_id" % byte_count_id

    finally:
      cursor.close()
  finally:
    conn.close()

