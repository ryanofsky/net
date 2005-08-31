page = """<html>
<body>

[if-any done]

[is done "lifted"]
<p>The blackout is now lifted</p>
[end]

[is done "enabled"]
<p>Blackout is enabled with the following blackout message:</p>
<hr>
<pre>[message]</pre>
[end]

[else]

<h3>Blackout Page</h3>

[if-any blackout]
<p>Blackout is currently <strong>enabled</strong>. Use the form below to
change the blackout message or lift the blackout.</p>
[else]
<p>Blackout is currently <strong>disabled</strong>. Use the form below to
enable blackout and set a blackout message.</p>
[end]

<table bgcolor="#dddddd" cellpadding=10><tr><td>
<p>Blackout Message:</p>
<form method=post>
<textarea name=message rows=20 cols=80>[message]</textarea><br>
<input type=submit name=enable value="[if-any blackout]Update Message[else]Enable Blackout[end]">
[if-any blackout]<input type=submit name=lift value="Lift Blackout">[end]
</form>
</td></tr></table>

[end]

<hr>
<p><a href="/">Back to Main Page</a></p>

</body>
</html>
"""

import cgi
import cStringIO
import base64

from mod_python import apache, util
from net import ezt, db, iptables, config

def index(req, enable=None, lift=None, message=None):

  done = None

  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      try:
        if enable:
          user = authenticate(req)
          if db.set_blackout(cursor, True, message):
            db.log(cursor, 'User %s enabling blackout with message %s' %
                           (db.log_str(user), db.log_str(message)))
            iptables.enable_blackout(cursor)
          else:
            db.log(cursor, 'User %s changing blackout message to %s' %
                           (db.log_str(user), db.log_str(message)))
          done = 'enabled'
          blackout = True
        elif lift:
          user = authenticate(req)
          if db.set_blackout(cursor, False):
            db.log(cursor, 'User %s lifting blackout' % db.log_str(user))
            iptables.disable_blackout(cursor)
          done = 'lifted'
          blackout = False
        else:
          if message is None:
            message = db.blackout_message(cursor)
          blackout = db.blackout_enabled(cursor)
      except apache.SERVER_RETURN:
        raise
      except:
        db.log_exception(cursor, 'BLACKOUT PAGE FATAL ERROR '
                                 '(url = %s, form = %s)'
                                 % (db.log_str(req.unparsed_uri), req.form.list))
        raise
    finally:
      cursor.close()
  finally:
    conn.close()

  vars = {
    'done': done,
    'blackout': ezt.boolean(blackout),
    'message': message and cgi.escape(message),
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
    if user == config.ADMIN_USER and passwd == config.ADMIN_PASSWORD:
      return user

  req.err_headers_out["WWW-Authenticate"] = 'Basic realm = "%s"' % "kalam"
  raise apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED
