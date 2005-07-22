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
