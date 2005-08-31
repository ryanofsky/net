page = """<html>
<head><title>Internet Status Page</title></head>
<body>
<h2>Internet Status Page</h2>
<table border=1>
  <tr>
    <td><strong>Internet Gateway</strong></td>
    <td>[if-any gate]<font color=green>Up</font>[else]<font color=red>Down</font> (Blackout)[end]</td>
  </tr>
  <tr>
    <td><strong>Satellite Link</strong></td>
    <td>[if-any sat]<font color=green>Up</font>[else]<font color=red>Down</font>[end]</td>
  </tr>
</table>
<p><a href="/">Back to Main Page<a></p>
<hr>
<div><small>Generated <i>[date]</i><br>
Note: more detailed connection statistics will be added soon.</small></div>
</body>
</html>
"""

import cgi
import cStringIO
import time
import socket
import select
import errno
import time

from net import ezt, addr, db, hosts

SAT_ADDR = ('203.110.192.17', 23)
TIMEOUT = 1.0

def connect_sat():
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  try:
    sock.setblocking(0)
    timeout = time.time() + TIMEOUT
    while True:
      result = sock.connect_ex(SAT_ADDR)
      if result in (0, errno.EISCONN):
        return 1
      if result in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
        readable, writable, special = select.select([], [sock], [], 
                                                    max(0, timeout - time.time()))
        if time.time() > timeout:
          return None
        continue
      return None
  finally:
    sock.close()

def index(req, outgoing='', sort=''):
  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      gate = ezt.boolean(not db.blackout_enabled(cursor))
    finally:
      cursor.close()
  finally:
    conn.close()

  sat = ezt.boolean(connect_sat())
  vars = {
    'date': time.strftime('%a %b %d %H:%M:%S %Z %Y'),
    'gate': gate,
    'sat': sat,
  }

  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()


