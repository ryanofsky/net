#!/usr/bin/env python

from net import db, hosts, addr
import sys

# start a new interval when more than SPLIT_SECONDS has elapsed between times
SPLIT_SECONDS = 3

# warn if spread over an interval is more than SPREAD_SECONDS
SPREAD_SECONDS = 5

# error if space between interval is less than SPACE_SECONDS without an
# an explicit SPLIT_TIME
SPACE_SECONDS = 15

# override interval assignment heuristic and start new intervals at the
# specified times
SPLIT_TIMES = (
  '2005-08-13 18:51:01',
  '2005-08-14 11:09:01',
  '2005-08-14 11:34:01',
  '2005-08-14 11:45:01',
  '2005-08-14 13:51:01',
  '2005-08-23 06:01:01',
  '2005-08-26 17:10:07',
  '2005-08-28 16:39:01',
  '2005-08-31 17:01:14',
)

# override interval assignment heuristic and never start new intervals
# at the specified times
JOIN_TIMES = (
  '2005-08-14 11:33:58',
  '2005-08-16 17:57:11',
  '2005-08-18 05:13:13',
  '2005-08-31 21:10:05',
  '2005-08-31 21:11:05',
  '2005-08-31 21:23:05',
  '2005-08-31 21:24:06',
  '2005-09-01 18:48:09',
)

SPLIT_TIMES = map(db.parse_time, SPLIT_TIMES)
JOIN_TIMES = map(db.parse_time, JOIN_TIMES)

def usage():
  sys.stderr.write("""\
Usage: migratecounts.py
Migrate to new counts schema
""")

def addfields(conn):
  cursor = conn.cursor()
  cursor.execute("""
CREATE TABLE byte_count_intervals
(
  interval_id INT NOT NULL AUTO_INCREMENT,
  end_time DATETIME NOT NULL,
  PRIMARY KEY (interval_id),
  UNIQUE KEY (end_time)
);
""")
  cursor.execute("ALTER TABLE byte_counts "
                 "ADD COLUMN interval_id INT NOT NULL AFTER end_time")

def investigate(center):
  return ("  (run SELECT * FROM byte_counts "
          "WHERE end_time > '%s' AND end_time < '%s';)"
          % (db.time_str(center - 200), db.time_str(center + 200)))

def addintervals(conn):
  cursor = conn.cursor()
  upcursor = conn.cursor()

  cursor.execute("SELECT byte_count_id, end_time, host_id FROM byte_counts "
                 "WHERE end_time is NOT NULL ORDER BY end_time")
  ends = []
  count_ids = []
  host_ids = []
  while True:
    row = cursor.fetchone()
    if row:
      count_id, end_time, host_id = row
      end = db.parse_time(end_time)

    if ends and (not row
                 or ((end - ends[-1] > SPLIT_SECONDS 
                      or (end in SPLIT_TIMES and not (ends and ends[-1] == end)))
                     and end not in JOIN_TIMES)):
      upcursor.execute("INSERT INTO byte_count_intervals (end_time) "
                       "VALUES (%s)", db.time_str(ends[0]))
      id = upcursor.lastrowid
      upcursor.execute("UPDATE byte_counts SET interval_id = %%s "
                       "WHERE byte_count_id IN (%s) "
                        % ",".join(map(str, count_ids)), id)
      spread = ends[-1] - ends[0]
      if spread > SPREAD_SECONDS:
        print ("WARNING: Interval '%s' - '%s' is %s seconds long"
               % (db.time_str(ends[0]), db.time_str(ends[-1]), spread))

      if row:
        space = end - ends[-1]
        if space < SPACE_SECONDS and end not in SPLIT_TIMES:
          print ("ERROR: Interval begins only %i seconds after previous ('%s' - '%s')"
                 % (space, db.time_str(ends[-1]), db.time_str(end)))
          print investigate(end)
      del ends[:]
      del count_ids[:]
      del host_ids[:]

    if not row:
      break

    # complain about fishy joins
    if (ends and end not in JOIN_TIMES):
      if host_id in host_ids:
        print ("ERROR host_id %i appears twice in interval %s to %s"
               % (host_id, db.time_str(ends[-1]), db.time_str(end)))
        print investigate(end)
      # test isn't right if times are more than a minute apart, but
      # that won't happen with sane values of split_count
      if ((end_time.minute == last_time.minute and last_time.second < 1 and end_time.second >= 1)
          or (end_time.minute == (last_time.minute + 1) % 60 and end_time.second >= 1)):
        print ("ERROR: no split between %s and %s over :01 second boundary"
               % (db.time_str(ends[-1]), db.time_str(end)))
        print investigate(end)

    ends.append(end)
    count_ids.append(count_id)
    host_ids.append(host_id)
    last_time = end_time

if __name__ == '__main__':
  if len(sys.argv) != 1:
    usage()
    sys.exit(1)

  conn = db.connect()
  addfields(conn)
  addintervals(conn)
  sys.exit(0)

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
