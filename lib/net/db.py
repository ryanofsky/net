import MySQLdb
import time
import calendar
import re
import config

DEBUG = False

def connect():
  db = MySQLdb.connect(user=config.MYSQL_USER, 
                       passwd=config.MYSQL_PASSWORD,
                       db=config.MYSQL_DATABASE)
  if DEBUG:
    db_query = db.query
    def query(s):
      print s
      return db_query(s)
    db.query = query
  return db

def lookup_host(cursor, mac):
  """Returns (ip, name, email) tuple or None"""
  if cursor.execute("SELECT ip_addr, name, email, status "
                    "FROM hosts WHERE mac_addr = %s", mac):
    return cursor.fetchone()
  return None

def update_host(cursor, mac, ip, name, email):
  cursor.execute("UPDATE hosts SET ip_addr=%s, name=%s, email=%s "
                 "WHERE mac_addr = %s", (ip, name, email, mac))

def insert_host(cursor, mac, ip, name, email):
  cursor.execute("INSERT INTO hosts (mac_addr, ip_addr, name, email, status) "
                 "VALUES (%s, %s, %s, %s, 'registered')",
                 (mac, ip, name, email))

def log(cursor, message):
  cursor.execute("INSERT INTO log (time, message) "
                 "VALUES (%s, %s)",
                 (time_str(), message))

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

REGISTERED = 'registered'
BLOCKED = 'blocked'

def get_hosts(cursor, status=None):
  sql = "SELECT name, ip_addr, mac_addr FROM hosts"
  args = []
  if status:
    sql += " WHERE status = %s"
    args.append(status)

  cursor.execute(sql, args)
  while True:
    row = cursor.fetchone()
    if not row:
      break
    yield row

def add_count(cursor, host_id, incoming, outgoing):
  time = time_str()
  
  if incoming == 0 and outgoing == 0:
    # optimized case, there's no reason to add subsequent rows with zero
    # counts, just update the end times

    cursor.execute("SELECT start_time "
                   "FROM byte_counts "
                   "WHERE host_id = %s AND end_time IS NULL", host_id)

    if cursor.rowcount:
      assert cursor.rowcount == 1
      old_time, = cursor.fetchone()
      
      cursor.execute("UPDATE byte_counts SET end_time = %s "
                     "WHERE host_id = %s AND end_time = %s "
                     "  AND incoming = 0 AND outgoing = 0", 
                     (time, host_id, old_time))

      if cursor.rowcount:
        assert cursor.rowcount == 1
        cursor.execute("UPDATE byte_counts SET start_time = %s "
                       "WHERE host_id = %s AND start_time = %s "
                       "  AND end_time IS NULL",
                       (time, host_id, old_time))
        assert cursor.rowcount == 1
        return

  # normal case
  cursor.execute("UPDATE byte_counts "
                 "SET incoming = %s, outgoing = %s, end_time = %s "
                 "WHERE host_id = %s AND end_time IS NULL",
                 (incoming, outgoing, time, host_id))

  if cursor.rowcount == 0:
    cursor.execute("INSERT INTO byte_counts "
                   "(host_id, start_time, end_time, incoming, outgoing) "
                   "VALUES (%s, %s, %s, %s, %s)",
                   (host_id, time, time, incoming, outgoing))

  cursor.execute("INSERT INTO byte_counts (host_id, start_time) "
                 "VALUES (%s, %s)", (host_id, time))

