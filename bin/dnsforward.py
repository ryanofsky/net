#!/usr/bin/env python

import sys
import socket
import select
import time
import _mysql_exceptions

from net import config, addr, hosts, db

BUFSIZE=5000
TIMEOUT=10.0

def run(cursor):
  server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server.bind(config.DNS_LISTEN)

  read_handles = [server]
  while True:
    if len(read_handles) > 1:
      timeout = max(0, read_handles[1].timeout - time.time())
    else:
      timeout = None

    readable, writeable, special = select.select(read_handles, [], [], timeout)
    now = time.time()

    for r in readable:
      if r is server:
        query, client_addr = server.recvfrom(BUFSIZE)
        print "RECIEVED QUERY FROM", repr(client_addr)

        client = Client(socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
                        client_addr, now + TIMEOUT)

        dest = forward_addr(cursor, client.addr)
        client.socket.sendto(query, dest)
        print "FORWARDED QUERY TO", repr(dest), "USING", repr(client.socket.getsockname())

        read_handles.append(client)

      else:
        client = r

        response, server_addr = client.socket.recvfrom(BUFSIZE)
        print "RECIEVED RESPONSE FOR", repr(client.socket.getsockname())

        server.sendto(response, client.addr)
        print "FORWARDED RESPONSE TO", repr(client.addr)

        read_handles.remove(client)

    for client in read_handles[1:]:
      if client.timeout < now:
        print "QUERY TIMED OUT"
        read_handles.remove(client)
      else:
        break

class Client:
  """Object to store client information while waiting for a response"""
  def __init__(self, socket, addr, timeout):
    self.socket = socket
    self.addr = addr
    self.timeout = timeout

  def fileno(self):
    return self.socket.fileno()

def forward_addr(cursor, client_addr):
  """Determine which DNS server a client's query should be forwarded to"""
  ip = addr.parse_ip(client_addr[0])
  host = hosts.lookup_ip(cursor, ip)
  if not host or host.blocked or not host.registered:
    return config.DNS_FORWARD

  return config.DNS_FORWARD_REGISTERED

if __name__ == '__main__':
  while True:
    try:
      conn = db.connect()
      try:
        cursor = conn.cursor()
        try:
          run(cursor)
        finally:
          cursor.close()
      finally:
        conn.close
    except _mysql_exceptions.OperationalError, e:
      print "Got mysql exception `%s', restarting in 10 seconds" % str(e)
      time.sleep(10)
