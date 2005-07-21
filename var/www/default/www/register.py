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
form below to update your registration information.</p>
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
    <td><input type=submit name=submit value=[if-any registered]Update[else]Register[end]></td>
  </tr>
</table>
</form>

[end]

</body>
</html>
"""
from net.ezt import Template
from net.addr import parse_ip, ip2mac, ip_str, mac_str
from net.db import connect, lookup_host, update_host, insert_host, log
import cStringIO
import cgi

def index(req, url=None, name=None, email=None):
  ip = parse_ip(req.connection.remote_ip)
  mac = ip2mac(ip)
  if mac is None: 
    raise "Could not determine MAC address for %s" % ip

  done = None
  errors = []
  if name == '':
    errors.append('You need to type your name.')

  db = connect()
  try:
    registered = lookup_host(db, mac)
    if registered:
      reg_ip, reg_name, reg_email = registered
      update = name or (ip != reg_ip and name is None)
      if name is None: name = reg_name
      if email is None: email = reg_email
      if update:
        update_host(db, mac, ip, name, email)
	msg = "Updated registration: mac = %s" % mac_str(mac)
	msg += ", name = `%s', old name = `%s'" % (name, reg_name)
	msg += ", email = `%s', old email = `%s'" % (email, reg_email)
	msg += ", ip = %s, old ip = %s" % (ip_str(ip), ip_str(reg_ip))
	log(db, msg)
	if ip == reg_ip:
          done = 'REGISTRATION UPDATED'
	else:
	  done = 'REGISTRATION UPDATED (host ip changed)'
    elif name:
      insert_host(db, mac, ip, name, email)
      log(db, "Added registration: mac = %s, ip = %s, "
              "name = `%s', email = `%s'"
               % (mac_str(mac), ip_str(ip), name, email))
    
      done = 'REGISTRATION COMPLETE'
  finally:
    db.close()

  vars = {
    'done': done,
    'errors': errors,
    'registered': registered,
    'name': name and cgi.escape(name, 1),
    'email': email and cgi.escape(email, 1),
    ### enable url when internet actually works
    'url': None and url and cgi.escape(url, 1),
  }
  out = cStringIO.StringIO()
  template = Template()
  template.parse(page)
  template.generate(out, vars)
  return out.getvalue()

