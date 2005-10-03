#!/usr/bin/env python

from net import hosts, db, addr
import sys
import urllib

from net.config import ADMIN_USER, ADMIN_PASSWORD
ADMIN_URL = 'http://192.168.10.1/'
DEBUG = False

class URLOpener(urllib.FancyURLopener):
  def prompt_user_passwd(self, host, realm):
    return ADMIN_USER, ADMIN_PASSWORD

def fetch(page, post_params):
  url = ADMIN_URL + page
  opener = URLOpener()
  fp = opener.open(url, post_params and urllib.urlencode(post_params) or None)
  fp.read()

def add_mac(mac, name):
  params = { 'name': name[:20].replace('"', "'") }
  mac = addr.mac_str(mac).split(':')
  for i in range(0, 6):
    params["mac%i" % (i+1)] = mac[i]
  fetch('mac.cgi', params)

def register():
  conn = db.connect()
  try:
    cursor = conn.cursor()
    try:
      for host in hosts.get_hosts(cursor):
        if host.registered and not host.blocked:
          print "Registering %s (%s)" % (addr.mac_str(host.mac), host.name)
          add_mac(host.mac, host.name)
    finally:
      cursor.close()
  finally:
    conn.close()

if __name__ == '__main__':
  if len(sys.argv) == 2 and sys.argv[1] == 'register':
    register()
  else:
    print "Usage: dlink.py register"
    print "Add registered hosts to dlink router's mac filter"
    sys.exit(1)
   
