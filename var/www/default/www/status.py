page = """<html>
<head><title>Internet Status Page</title></head>
<body>
<h2>Internet Status Page</h2>
<table border=1>
  <tr>
    <td><strong>Internet Gateway</strong></td>
    <td>[if-any gate][is gate "1"]<font color=green>Up</font>[else]<font color=red>Down</font> (Blackout)[end][else]&nbsp;[end]</td>
  </tr>
  <tr>
    <td><strong>Satellite Modem</strong></td>
    <td>[if-any modem][is modem "1"]<font color=green>Up</font>[else]<font color=red>Down</font>[end][else]&nbsp;[end]</td>
  </tr>
 <tr>
    <td><strong>Satellite Link</strong></td>
    <td>[if-any link][is link "1"]<font color=green>Up</font>[else]<font color=red>Down</font>[end][else]&nbsp;[end]</td>
  </tr>
</table>
<p><a href="/">Back to Main Page<a></p>
<hr>
<div><small>Generated <i>[date]</i><br>
</body>
</html>
"""

import cgi
import cStringIO
import time
import socket
import select
import errno

from net import ezt, addr, db, hosts, asynch

ON_ADDR = ('203.110.192.17', 23)
OFF_ADDR = ('10.1.23.166', 23)

TIMEOUT = 1.0

class TestSatOp(asynch.Fiber):
  def run(self, reactor):
    onsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reactor.prep_socket(onsock)
    onconn = asynch.ConnectOp(reactor, onsock, ON_ADDR)

    offsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reactor.prep_socket(offsock)
    offconn = asynch.ConnectOp(reactor, offsock, OFF_ADDR)

    timeout = asynch.Timeout(reactor, TIMEOUT)

    self.on_up = False
    self.off_up = False
  
    while onconn or offconn:
      yield onconn, offconn, timeout

      if onconn and onconn.done():
        if not onconn.error:
          self.on_up = True
          offconn = None
        onconn = None

      if offconn and offconn.done():
        if not offconn.error:
          self.off_up = True
          onconn = None
        offconn = None

      if timeout.done():
        offconn = onconn = None

    onsock.close()
    offsock.close()

def connect_sat():
  reactor = asynch.Reactor()
  test_sat = TestSatOp(reactor)
  reactor.run(test_sat)
  if test_sat.on_up:
    return True, True
  elif test_sat.off_up:
    return True, False
  else:
    return False, None

def ezt_tribool(val):
  if val is None:
    return None
  elif val is True:
    return "1"
  elif val is False:
    return "0"
  assert False

def index(req, outgoing='', sort=''):
  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      gate = not db.blackout_enabled(cursor)
    finally:
      cursor.close()
  finally:
    conn.close()

  modem, link = connect_sat()
  vars = {
    'date': time.strftime('%a %b %d %H:%M:%S %Z %Y'),
    'gate': ezt_tribool(gate),
    'modem': ezt_tribool(modem),
    'link': ezt_tribool(link),
  }

  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()


