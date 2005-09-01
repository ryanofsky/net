#!/usr/bin/env python

import sys

from net import db, hosts, addr

db.DEBUG = True

def usage():
  sys.stderr.write("""\
Usage: fixcounts.py
Fix byte count rows with start time > end time due to clock change
""")

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  conn = db.connect()
  cursor = conn.cursor()
  adjcursor = conn.cursor()
  fixcursor = conn.cursor()
 
  cursor.execute("SELECT byte_count_id, host_id, start_time, end_time, "
                 "incoming, outgoing "
                 "FROM byte_counts WHERE start_time > end_time "
                 "ORDER BY byte_count_id")
  while True:
    row = cursor.fetchone()
    if not row:
      break
         
    count_id, host_id, start_time, end_time, incoming, outgoing = row
    print ("Invalid row %s, host = %s, start = %s, end = %s, "
           "incoming = %s, outgoing = %s"
            % (count_id, host_id, start_time, end_time, incoming, outgoing))
 
    delete_ids = [count_id]
 
    adjcursor.execute("SELECT byte_count_id, start_time, end_time, "
                      "incoming, outgoing "
                      "FROM byte_counts WHERE host_id = %s AND "
                      "byte_count_id > %s AND end_time <= %s "
                      "ORDER BY byte_count_id",
                      (host_id, count_id, start_time))
    while True:
      row = adjcursor.fetchone()
      if not row:
        break

      adj_id, adj_start, adj_end, adj_in, adj_out = row
      print ("Invalid adjacent row %s, host = %s, start = %s, end = %s, "
             "incoming = %s, outgoing = %s"
              % (adj_id, host_id, adj_start, adj_end, adj_in, adj_out))
           
      delete_ids.append(adj_id)
      incoming += adj_in
      outgoing += adj_out
      end_time = adj_end
   
    adjcursor.execute("SELECT byte_count_id, start_time, end_time, "
                      "incoming, outgoing FROM byte_counts "
                      "WHERE host_id = %s AND start_time = %s "
                      "ORDER BY byte_count_id LIMIT 1",
                      (host_id, end_time))
    if adjcursor.rowcount == 0:
      print "ERROR: Could not find follow-on row to add deleted counts to"
    else:
      adj_id, adj_start, adj_end, adj_in, adj_out = adjcursor.fetchone()
      print ("Updating follow-on row %s, host = %s, start = %s, end = %s, "
             "incoming = %s, outgoing = %s"
              % (adj_id, host_id, adj_start, adj_end, adj_in, adj_out))
      fixcursor.execute("UPDATE byte_counts SET start_time = %s, "
                        "incoming = %s, outgoing = %s "
                        "WHERE byte_count_id = %s",
                        (start_time, incoming + adj_in, outgoing + adj_out,
                         adj_id))
      fixcursor.execute("DELETE FROM byte_counts WHERE byte_count_id IN (%s)"
                        % ",".join(map(str, delete_ids)))
    print
