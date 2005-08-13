import db, iptables, addr

class Host:
  def __init__(self, id, mac, ip, name, email, registered, blocked):
    self.id = id
    self.mac = mac
    self.ip = ip
    self.name = name
    self.email = email
    self.registered = registered
    self.blocked = blocked

  def insert(self, cursor):
    """Insert new host into sql database and update iptables"""
    db.log(cursor, "Adding host: mac = %s, ip = %s, "
                   "name = %s, email = %s, registered = %s, blocked = %s"
                   % (addr.mac_str(self.mac), addr.ip_str(self.ip),
                      db.log_str(self.name), db.log_str(self.email),
                      self.registered, self.blocked))

    # if there is another host with the same ip, zero it out
    other = lookup_ip(cursor, self.ip)
    if other:
      assert other.mac != self.mac
      other.update(cursor, ip=None)

    self.id = db.insert_host(cursor, self.mac, self.ip, self.name,
                             self.email, self.registered, self.blocked)
    self.iptables_add(cursor)

  def update(self, cursor, **fields):
    """Change information about this host and update sql database and iptables"""

    # rote argument handling
    new_ip = self.ip
    new_name = self.name
    new_email = self.email
    new_registered = self.registered
    new_blocked = self.blocked

    log_args = []

    if fields.has_key('ip'):
      new_ip = fields['ip']
      log_args += ['ip', self.ip and addr.ip_str(self.ip),
                   new_ip and addr.ip_str(new_ip)]
      del fields['ip']

    if fields.has_key('name'):
      new_name = fields['name']
      log_args += ['name', db.log_str(self.name), db.log_str(new_name)]
      del fields['name']

    if fields.has_key('email'):
      new_email = fields['email']
      log_args += ['email', db.log_str(self.email), db.log_str(new_email)]
      del fields['email']

    if fields.has_key('registered'):
      new_registered = fields['registered']
      log_args += ['registered', self.registered, new_registered]
      del fields['registered']

    if fields.has_key('blocked'):
      new_blocked = fields['blocked']
      log_args += ['blocked', self.blocked, new_blocked]
      del fields['blocked']

    if fields:
      raise TypeError, "Unexpected keyword argument(s): " + ", ".join(fields.keys())

    db.log(cursor, 'Updating host: id = %s, mac = %s'
                   % (self.id, addr.mac_str(self.mac))
                   + (', %s %s => %s' * (len(log_args)/3)) % tuple(log_args))

    # if there is another host with the new ip, zero it out
    other = new_ip and new_ip != self.ip and lookup_ip(cursor, new_ip)
    if other:
      assert other.mac != self.mac
      other.update(cursor, ip=None)

    # figure out what to do with iptables
    is_registered = self.registered and not self.blocked
    will_be_registered = new_registered and not new_blocked
    do_del = ((is_registered and (not will_be_registered or new_ip != self.ip))
              or (self.blocked and not new_blocked))
    do_add = ((will_be_registered and (not is_registered or new_ip != self.ip))
              or (new_blocked and not self.blocked))

    # delete existing entries from iptables, if neccessary, before applying updates
    if do_del:
      self.iptables_del(cursor)

    # apply updates
    self.ip = new_ip
    self.name = new_name
    self.email = new_email
    self.registered = new_registered
    self.blocked = new_blocked

    db.update_host(cursor, self.mac, self.ip, self.name, self.email,
                   self.registered, self.blocked)

    # add iptables entries, if neccessary
    if do_add:
      self.iptables_add(cursor)

  def iptables_add(self, cursor):
    if self.blocked:
      iptables.add_blocked(cursor, self.mac)
    elif self.registered and self.ip is not None:
      db.add_count(cursor, self.id, 0, 0)
      iptables.add_registered(cursor, self.ip, self.mac)

  def iptables_del(self, cursor):
    if self.blocked:
      iptables.del_blocked(cursor, self.mac)
    elif self.registered and self.ip is not None:
      ### should save byte counts before deleting rule here
      iptables.del_registered(cursor, self.ip, self.mac)


def lookup_mac(cursor, mac):
  row = db.lookup_host_with_mac(cursor, mac)
  return row and Host(*row)


def lookup_ip(cursor, ip):
  row = db.lookup_host_with_ip(cursor, ip)
  return row and Host(*row)


def get_hosts(cursor):
  for row in db.get_hosts(cursor):
    yield Host(*row)
