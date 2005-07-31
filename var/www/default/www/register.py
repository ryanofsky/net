page = """<html>
<body>

[if-any done]
<p>[done]</p>
[if-any url]<p>Click <a href="[url]">here</a> to procede to <strong>[url]</strong>[end]
[else]
  [if-any errors]
<ul>
  [for errors]
  <li><font color=red>[errors]</font></li>
  [end]
</ul>
  [end]

  [if-any registered]
<h3>Update your registration</h3>
<p>Your computer has already been registered on this network. You can use the
form below to update your registration information or unregister.</p>
  [else]
<h3>Register your computer</h3>
<p>To access the internet, you need to register your computer on this network.
Just enter your name in the form below, hit "Register," and your computer will
be permanently registered. Registration helps the network adminstrators
monitor individual bandwidth usage and block unauthorized users, for faster
internet access.</p>
  [end]

<form method=post>

<table border=0>
  <tr>
    <td><label for=name>Name:</label></td>
    <td><input type=text name=name[if-any name] value="[name]"[end] id=name></td>
  </tr>
  <tr>
    <td><label for=email>Email (optional):</label></td>
    <td><input type=text name=email[if-any email] value="[email]"[end] id=email></td>
  </tr>
  <tr>
    <td>&nbsp;</td>
    <td>
      <input type=submit name=submit value=[if-any registered]Update[else]Register[end]>
      [if-any registered]<input type=submit name=unregister value=Unregister>[end]
    </td>
  </tr>
</table>
</form>

[end]

</body>
</html>
"""

import cgi
import cStringIO

from net import ezt, addr, db, hosts

def index(req, url=None, name=None, email=None, unregister=None):
  ip = addr.parse_ip(req.connection.remote_ip)
  mac = addr.ip2mac(ip)
  if mac is None:
    raise "Could not determine MAC address for %s" % ip

  done = None
  errors = []
  registered = None

  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      try:
        host = hosts.lookup_mac(cursor, mac)
        if unregister is not None:
          if host:
            host.update(cursor, registered=False, ip=ip)
          done = 'REGISTRATION REMOVED'
          url = None

        elif name is not None:
          if not name:
            errors.append('You need to type your name')

          if not errors:
            if host:
              done = 'REGISTRATION UPDATED'
              host.update(cursor, name=name, email=email, registered=True, ip=ip)
            else:
              done = 'REGISTRATION ADDED'
              host = hosts.Host(None, mac, ip, name, email, True, False)
              host.insert()

        elif host and host.ip != ip:
          done = ('REGISTRATION IP ADDRESS UPDATED (WAS %s, IS %s)'
                   % (addr.ip_str(host.ip), addr.ip_str(ip)))
          host.update(cursor, ip=ip)

        if not done:
          if name is None and host and host.registered:
            registered = True
            name = host.name
            email = host.email

      except:
        db.log_exception(cursor, 'REGISTRATION PAGE FATAL ERROR '
                                 '(ip = %s, mac = %s, url = %s, form = %s)'
                                 % (addr.ip_str(ip), addr.mac_str(mac),
                                    db.log_str(req.unparsed_uri), req.form.list))
        raise
    finally:
      cursor.close()
  finally:
    conn.close()

  vars = {
    'done': done,
    'errors': errors,
    'registered': registered,
    'name': name and cgi.escape(name, True),
    'email': email and cgi.escape(email, True),
    ### enable url when internet actually works
    'url': None and url and cgi.escape(url, True),
  }
  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()

