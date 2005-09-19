page = """<html>
<head><title>Block Users</title></head>

<body>

<h3>Block Users</h3>


[if-any changes]
<div style="background-color: #FFAAAA">
<p><strong>The following changes have been made:</strong></p>
<ul>
[for changes]
  <li>[changes]</li>
[end]
</ul>
</div>
<p><a href="/">Back to Main Page</a></p>
[end]

<p>Use the check boxes next to registration names to block or unblock users,
then hit the "Save Changes" button to put your changes into effect.</p>

<form method=post>
<table><tr><td>
<table border=1>
<thead>
<tr>
  <td><strong>[is sortby "name"]Name[else]<a href="[uri]?sortby=name">Name</a>[end]</strong></td>
  <td><strong>[is sortby "since"]Registered Since[else]<a href="[uri]?sortby=since">Registered Since</a>[end]</strong></td>
</tr>
</thead>
<tbody>
[for hosts]
<tr>
  <td>
  <input type=checkbox name=block id=block[hosts.id] value="[hosts.id]" [if-any hosts.blocked] checked[end]>[if-any hosts.blocked]<input type=hidden name=blocked value="[hosts.id]">[end]
  <label for=block[hosts.id]>[hosts.name]</label></td>
  <td>[hosts.since]</td>
</tr>
[end]
</tbody>
</table>
<p align=center><input type=submit name=submit value="Save Changes"></p>
</td></tr></table>
</form>

<hr>
<p><a href="/">Back to Main Page</a></p>

</body>
</html>
"""

import cgi
import cStringIO
import base64
import time

from mod_python import apache, util
from net import ezt, db, iptables, config, hosts

class Host:
  def __init__(self, id, name, since, blocked):
    self.id = id
    self.name = cgi.escape(name)
    self.name_cmp = name.lower()
    self.since = time.strftime('%a %b %d %H:%M:%S %Z %Y', time.localtime(since))
    self.since_cmp = since
    self.blocked = ezt.boolean(blocked)

def index(req):
  changes = []
  host_list = []

  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      try:
        block = map(int, req.form.getlist('block'))
        blocked = map(int, req.form.getlist('blocked'))

        if block or blocked:
          user = authenticate(req)

          for id in blocked:
            if id not in block:
              host = hosts.lookup_id(cursor, id)
              if host:
                host.update(cursor, blocked=False)
                changes.append('<i>%s</i> unblocked' % cgi.escape(host.name))

          for id in block:
            if id not in blocked:
              host = hosts.lookup_id(cursor, id)
              if host:
                host.update(cursor, blocked=True)
                changes.append("<i>%s</i> blocked" % cgi.escape(host.name))

          if not changes:
            changes.append("<i>No changes</i>")

        for host in hosts.get_hosts(cursor):
          if host.registered:
            host_list.append(Host(host.id, host.name, host.since, host.blocked))

        sortby = req.form.getfirst('sortby')
        if sortby == 'name':
          host_list.sort(lambda x, y: cmp(x.name_cmp, y.name_cmp))
        else:
          sortby = 'since'
          host_list.sort(lambda x, y: -cmp(x.since_cmp, y.since_cmp))

      except apache.SERVER_RETURN:
        raise
      except:
        db.log_exception(cursor, 'BLOCK PAGE FATAL ERROR '
                                 '(url = %s, form = %s)'
                                 % (db.log_str(req.unparsed_uri), req.form.list))
        raise
    finally:
      cursor.close()
  finally:
    conn.close()

  vars = {
    'changes': changes,
    'hosts': host_list,
    'uri': req.uri,
    'sortby': sortby,
  }
  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()

def authenticate(req):
  if req.headers_in.has_key("Authorization"):
    s = req.headers_in["Authorization"][6:]
    s = base64.decodestring(s)
    user, passwd = s.split(":", 1)
    if (user.lower() == config.ADMIN_USER.lower()
        and passwd.lower() == config.ADMIN_PASSWORD.lower()):
      return user

  req.err_headers_out["WWW-Authenticate"] = 'Basic realm = "%s"' % "kalam"
  raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED
