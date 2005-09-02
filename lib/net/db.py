import MySQLdb
import time
import calendar
import re
import types
import traceback
import cStringIO
import sys

import config

DEBUG = False

def connect():
  db = MySQLdb.connect(user=config.MYSQL_USER,
                       passwd=config.MYSQL_PASSWORD,
                       db=config.MYSQL_DATABASE,
                       client_flag=_CLIENT_FOUND_ROWS)
  if DEBUG:
    db_query = db.query
    def query(s):
      print s
      return db_query(s)
    db.query = query
  return db

def lookup_host_with_mac(cursor, mac):
  if cursor.execute("SELECT host_id, mac_addr, ip_addr, name, email, "
                      "registered, blocked "
                    "FROM hosts WHERE mac_addr = %s", mac):
    assert cursor.rowcount == 1
    return cursor.fetchone()
  return None

def lookup_host_with_ip(cursor, ip):
  if cursor.execute("SELECT host_id, mac_addr, ip_addr, name, email, "
                      "registered, blocked "
                    "FROM hosts WHERE ip_addr = %s", ip):
    assert cursor.rowcount == 1
    return cursor.fetchone()
  return None

def lookup_host_with_id(cursor, id):
  if cursor.execute("SELECT host_id, mac_addr, ip_addr, name, email, "
                      "registered, blocked "
                    "FROM hosts WHERE host_id = %s", id):
    assert cursor.rowcount == 1
    return cursor.fetchone()
  return None

def insert_host(cursor, mac, ip, name, email, registered, blocked):
  """Insert host record with specified values"""
  cursor.execute("INSERT INTO hosts (mac_addr, ip_addr, name, email, "
                                    "registered, blocked) "
                 "VALUES (%s, %s, %s, %s, %s, %s)",
                 (mac, ip, name, email, _bool(registered), _bool(blocked)))
  return cursor.lastrowid

def update_host(cursor, mac, ip, name, email, registered, blocked):
  """Update host record with specified values"""
  if cursor.execute("UPDATE hosts SET ip_addr = %s, name = %s, email = %s, "
                    "registered = %s, blocked = %s WHERE mac_addr = %s",
                    (ip, name, email, _bool(registered), _bool(blocked),
                     mac)):
    assert cursor.rowcount == 1
    return True
  return False

def get_hosts(cursor):
  cursor.execute("SELECT host_id, mac_addr, ip_addr, name, email, "
                 "registered, blocked FROM hosts")
  while True:
    row = cursor.fetchone()
    if row:
      yield row
    else:
      break

def log(cursor, message):
  cursor.execute("INSERT INTO log (time, message) VALUES (%s, %s)",
                 (time_str(), message))

def log_exception(cursor, message):
  fp = cStringIO.StringIO()
  fp.write(message)
  fp.write('\n')
  traceback.print_exc(None, fp)
  log(cursor, fp.getvalue())

def log_str(s):
  if type(s) in types.StringTypes:
    return "'%s'" % s.replace("'", "\ \'")
  return str(s)

def time_str(ticks=None):
  """Return a MySQL DATETIME value from a unix timestamp"""
  if ticks is None:
    t = time.gmtime()
  else:
    t = time.gmtime(ticks)
  return "%04d-%02d-%02d %02d:%02d:%02d" % t[:6]

_re_datetime = re.compile('([0-9]{4})-([0-9][0-9])-([0-9][0-9]) '
                          '([0-9][0-9]):([0-9][0-9]):([0-9][0-9])')

def parse_time(datetime):
  """Return a unix timestamp from a MySQL DATETIME value"""
  if type(datetime) == types.StringType:
    # datetime is a MySQL DATETIME string
    matches = _re_datetime.match(datetime).groups()
    t = tuple(map(int, matches)) + (0, 0, 0)
  elif hasattr(datetime, "timetuple"):
    # datetime is a Python >=2.3 datetime.DateTime object
    t = datetime.timetuple()
  else:
    # datetime is an eGenix mx.DateTime object
    t = datetime.tuple()

  return calendar.timegm(t)

def blackout_enabled(cursor):
  cursor.execute("SELECT 1 FROM globals WHERE name = 'blackout' "
                 "AND value IS NOT NULL")
  return cursor.rowcount > 0

def blackout_message(cursor):
  cursor.execute("SELECT value FROM globals WHERE name = 'blackout_message'")
  row = cursor.fetchone()
  return row and row[0]

def set_blackout(cursor, enabled=None, message=None):
  if message is not None:
    cursor.execute("UPDATE globals SET value = %s "
                   "WHERE name = 'blackout_message'", message)
    if not cursor.rowcount:
      cursor.execute("INSERT INTO globals (name, value) "
                     "VALUES ('blackout_message', %s)",
                     message)

  if enabled is not None:
    enabled_now = blackout_enabled(cursor)
    if enabled and not enabled_now:
      cursor.execute("UPDATE globals SET value = 'enabled' "
                     "WHERE name = 'blackout'")
      if not cursor.rowcount:
        cursor.execute("INSERT INTO globals (name, value) "
                       "VALUES ('blackout', 'enabled')")
      return True
    elif not enabled and enabled_now:
      cursor.execute("UPDATE globals SET value = NULL "
                     "WHERE name = 'blackout'")
      return True

  return False

def add_interval(cursor, time=None):
  time = time_str(time)
  cursor.execute("INSERT INTO byte_count_intervals (end_time) VALUES (%s)", time)
  return cursor.lastrowid

def add_count(cursor, host_id, interval_id, incoming, outgoing):
  if incoming == 0 and outgoing == 0:
    # optimized case, there's no reason to add subsequent rows with zero
    # counts, just update the end times
    cursor.execute("SELECT byte_count_id, interval_id, incoming, outgoing "
                   "FROM byte_counts WHERE host_id = %s "
                   "ORDER BY interval_id DESC LIMIT 1", host_id)

    if cursor.rowcount:
      assert cursor.rowcount == 1
      count_id, row_interval_id, row_incoming, row_outgoing = cursor.fetchone()

      if row_incoming == 0 and row_outgoing == 0:
        cursor.execute("UPDATE byte_counts SET interval_id = %s "
                       "WHERE byte_count_id = %s",
                       (interval_id, count_id))
        assert cursor.rowcount == 1
        return

  # normal case
  cursor.execute("INSERT INTO byte_counts (host_id, interval_id, incoming, "
                 "outgoing) VALUES (%s, %s, %s, %s)",
                 (host_id, interval_id, incoming, outgoing))

class FakeCursor:
  def __init__(self, connection):
    self.connection = connection
  def execute(self, sql, args=None):
    if DEBUG:
      if args is not None:
        sql = sql % self.connection.literal(args)
      print "(FAKE)", sql
    self.rowcount = 1
    self.lastrowid = -1

def _bool(val):
  """Work around bug in MySQLdb escaping of bools

  When substituting python booleans into %s patterns, MySQLdb makes them into
  string literals. So,

    cursor.execute("SELECT %s", (False,))   becomes  SELECT 'False'
    cursor.execute("SELECT %s", (True,))    becomes  SELECT 'True'

  This is inconvenient, and inconsistent with the way MySQLdb handles other
  python types like NoneType.

    cursor.execute("SELECT %s", (None,))    becomes  SELECT NULL

  This function converts booleans to a form mysql won't mangle.
  """
  if type(val) is types.BooleanType:
    if val:
      return 1
    else:
      return 0
  return val


# From mysql_com.h, this client flag makes cursor.rowcount (which is set by
# mysql_affected_rows() from the C API) reflect the number of rows matched by
# an UPDATE statement instead of the number of rows physically changed by it.
# This is more consistent with other DBI interfaces and allows the use of the
# following idiom for updating existing rows instead of inserting duplicates
#
#   cursor.execute("UPDATE dict SET definition = %s WHERE word = %s")
#   if not cursor.rowcount:
#     cursor.execute("INSERT INTO dict (definition, word) VALUES (%s, %s))
#
# which, without the flag, would wrongly insert a duplicate row when the
# values in an existing row didn't change.
_CLIENT_FOUND_ROWS = 0x2
