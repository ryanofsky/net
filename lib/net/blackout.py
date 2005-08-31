from mod_python import apache, util

import db

def handler(req):
  req.content_type = 'text/html'
  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      req.write(db.blackout_message(cursor))
    finally:
      cursor.close()
  finally:
    conn.close()
  return apache.OK
