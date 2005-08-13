page = """<html>
<body>

[if-any done]

[is done "added"]
<h3>Added Registration</h3>
<p>Your computer is now registered, and should be able to access the 
internet. The registration is permanent, so unless you get a new computer
or manually delete your registration, you won't have to worry about
registering again.</p>

<p>You can update or delete your registration at any time by going to 
<a href="http://kalam/">http://kalam/</a>. That page also provides up-to-date
information about satellite connectivity and bandwidth usage.</p>
[end]

[is done "updated"]
<h3>Updated registration</h3>
<p>Your registration information has been updated.</p>
[end]

[is done "updated_ip"]
<h3>Updated registration IP</h3>
<p>Your computer's IP address has recently changed from [old_ip] to [ip]. This
change is now stored in the registration database and you computer should be 
able to access the internet again.</p>
[end]

[is done "removed"]
<h3>Removed Registration</h3>
<p>Your computer has been unregistered and will no longer be granted access
to the internet.</p>
[end]

[if-any url]<p>Click <a href="[url]">here</a> to procede to 
<strong>[url]</strong>.</p>

<p>(If this link bounces you back to the registration page, it might be 
necessary for you to restart your web browser.)</p>
[end]

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
<h3>B Co 2/69, 2nd Platoon Internet</h3>
<h4>Register your computer</h4>
<p>Starting August 13, in order to access the internet, you'll need to register
your computer on the network. Just enter your name in the form below, hit 
"Register," and your computer will be permanently registered. Registration
helps the network administrators monitor individual bandwidth usage and block
unauthorized users, for faster internet access.</p>
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

[if-any url][else]
<p><a href="/">Back to Main Page</a></p>
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
        old_ip = host and host.ip
        if unregister is not None:
          if host:
            host.update(cursor, registered=False, ip=ip)
          done = 'removed'
          url = None

        elif name is not None:
          if not name:
            errors.append('You need to type your name')

          if not errors:
            if host and host.registered:
              done = 'updated'
            else:
              done = 'added'

            if host:
              host.update(cursor, name=name, email=email, registered=True, ip=ip)
            else:
              host = hosts.Host(None, mac, ip, name, email, True, False)
              host.insert(cursor)

        elif host and host.ip != ip:
          done = 'updated_ip'
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
    'ip': ip and addr.ip_str(ip),
    'old_ip': old_ip and addr.ip_str(old_ip),
    'errors': errors,
    'registered': registered,
    'name': name and cgi.escape(name, True),
    'email': email and cgi.escape(email, True),
    ### enable url when internet actually works
    'url': url and cgi.escape(url, True),
  }
  out = cStringIO.StringIO()
  template = ezt.Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()

