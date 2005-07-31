page = """<html>
<head><title>[title]</title></head>
<body>
<h2>[title]</h2>
<p><a href="[switch_href]">[switch_text]</p>
<table border=1>
<thead>
  <tr>
    <td><strong>Host</strong></td>
    [for periods]
    [if-any periods.sort_href]
    <td><strong><a href="[periods.sort_href]">[periods.name]</a></strong></td>
    [else]
    <td><strong><i>[periods.name]</i></strong></td>
    [end]
    [end]
  </tr>
</thead>
<tbody>
[for hosts]
  <tr>
    <td>[hosts.name]</td>
    [for hosts.periods]
    <td>[if-any hosts.periods][hosts.periods][else]&nbsp;[end]</td>
    [end]
  </tr>
[end]
</tbody>
</table>
"""

import cgi
import cStringIO
import time

from net import ezt, addr, db, hosts

class Period:
  def __init__(self, name, duration):
    self.name = name
    self.duration = duration
    self.sort_href = None

class Host:
  def __init__(self, name, periods):
    self.name = name
    self.periods = periods
    self.sortby = None

  def __cmp__(self, other):
    if self.sortby is None:
      if other.sortby is None:
        return 0
      else:
        return 1
    else:
      if other.sortby is None:
        return -1
      else:
        return -cmp(self.sortby, other.sortby)

def commify(number):
  """Format a non-negative integer with commas"""
  n = str(number)
  l = len(n)
  return ','.join((l%3 and [n[:l%3]] or [])
                  + [n[i:i+3] for i in range(l%3, l, 3)])

def index(req, outgoing='', sort=''):
  periods = [
    Period('Last 7 Days', 7 * 24 * 60 * 60),
    Period('Last 24 Hours', 24 * 60 * 60),
    Period('Last 6 Hours', 6 * 60 * 60),
    Period('Last Hour', 60 * 60),
    Period('Last 10 Minutes', 10 * 60),
  ]
  host_list = []

  try:
    sort = int(sort)
  except ValueError:
    sort = 0
  else:
    if sort > len(periods):
      sort = 0

  period_idx = 0
  for period in periods:
    if sort != period_idx:
      params = '&'.join((outgoing and ('outgoing=1',) or ())
                        + (period_idx and ('sort=%i' % period_idx,) or ()))
      period.sort_href = cgi.escape(req.uri + (params and '?' + params), 1)
    period_idx += 1
  
  if outgoing:
    title = "Outgoing Bytes"
    switch_text = "Click to switch to incoming bytes"
    switch_href = cgi.escape(req.uri + (sort and '?sort=%i'%sort or ''), True)
  else:
    title = "Incoming Bytes"
    switch_text = "Click to switch to outgoing bytes"
    switch_href = cgi.escape(req.uri + '?outgoing=1' 
                             + (sort and '&sort=%i'%sort or ''), True)

  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      now = time.time()
      host_idx = {}
      for h in hosts.get_hosts(cursor):
        if h.registered:
          host_idx[h.id] = host = Host(cgi.escape(h.name), [None] * len(periods))
          host_list.append(host)

      period_idx = 0
      for period in periods:
        cursor.execute("SELECT host_id, SUM(%s) "
                       "FROM byte_counts "
                       "WHERE end_time > %%s "
                       "GROUP BY host_id" % (outgoing and "outgoing" or "incoming"), 
                       db.time_str(now - period.duration))
        while True:
          row = cursor.fetchone()
          if not row:
            break
          host_id, bytes = row
          try:
            host = host_idx[host_id]
          except KeyError:
            pass
          else:
            host.periods[period_idx] = commify(int(bytes))
            if period_idx == sort:
              host.sortby = bytes
  
        period_idx += 1
    finally:
      cursor.close()
  finally:
    conn.close()

  host_list.sort()
 
  vars = {
    'title': title,
    'switch_href': switch_href,
    'switch_text': switch_text,
    'hosts': host_list,
    'periods': periods,
  }
  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()


