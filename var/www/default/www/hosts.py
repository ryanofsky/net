from net import hosts, db, addr

def index():
  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      return ''.join(['%s %s\n' % (host.name, addr.mac_str(host.mac))
                      for host in hosts.get_hosts(cursor)])
    finally:
      cursor.close()
  finally:
    conn.close()
