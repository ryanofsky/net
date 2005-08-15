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
      cursor.execute("SELECT byte_count_id, host_id, start_time, end_time, "
                        "incoming, outgoing "
                     "FROM byte_counts ORDER BY host_id, byte_count_id")
      while True:
        row = cursor.fetchone()
        if not row:
          break
        byte_count_id, host_id, start_time, end_time, incoming, outgoing = row
        start = db.parse_time(start_time)
        end = end_time and db.parse_time(end_time)

        if host_id == last_host_id:
          if last_end is None:
            print ("ERROR row %i, host %i follows previous row %i "
                   "with NULL end time"
                   % (byte_count_id, host_id, last_byte_count_id))
          elif start != last_end:
            print ("ERROR row %i, host %i has start_time %s != "
                   "prev end time %s row %s" 
                   % (byte_count_id, host_id, start_time,
                      last_end_time, last_byte_count_id))

        elif last_host_id is not None:
          if last_end is not None:
            print ("WARNING final row %i, host %i is non-NULL"
                   % (last_byte_count_id, last_host_id))

        if end is None:
          if incoming is not None or outgoing is not None:
            print ("ERROR row %i, host %i has NULL end time "
                   "but non-null counts"
                   % (byte_count_id, host_id))
        else:
          if end < start:
            print ("ERROR row %i, host %i: start time %s > end time %s"
                   % (byte_count_id, host_id, start_time, end_time))
          elif end == start and host_id == last_host_id:
            print ("WARNING row %i, host %i: start time %s == end time %s" \
                   % (byte_count_id, host_id, start_time, end_time))

          if incoming is None or outgoing is None:
            print ("ERROR row %s, host %i has NULL byte counts"
                   % (byte_count_id, host_id))
          elif (incoming == 0 and outgoing == 0 and host_id == last_host_id
                   and last_incoming == 0 and last_outgoing == 0):
            print ("WARNING row %i, host %i has 0 counts and follows row %i "
                   "which also has zero counts"
                   % (byte_count_id, host_id, last_byte_count_id))
  
        last_host_id = host_id
        last_end = end
        last_end_time = end_time
        last_byte_count_id = byte_count_id
        last_incoming = incoming
        last_outgoing = outgoing
       
    finally:
      cursor.close()
  finally:
    conn.close()

