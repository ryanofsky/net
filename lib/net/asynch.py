import cStringIO
import time
import socket
import select
import errno
import time


class AsynchOp:
  def __init__(self, *args, **kwargs):
    """Create instance and call start() if given arguments"""
    self._hooks = []
    if args or kwargs:
      self.start(*args, **kwargs)

  def start(self, reactor):
    """Start operation asynchronously"""
    raise NotImplementedError

  def done(self):
    """Return True if operation completed.

    Calling this function before the operation has been started
    yields undefined results."""
    raise NotImplementedError

  def kick(self):
    """Wake this operation up to update it's state
    
    Only needed for operations that don't recieve notifications from a
    reactor."""
    pass

  def _notify(self):
    """Handle notification from reactor

    Should return False to stop recieving notifications, True otherwise"""
    raise NotImplementedError

  def add_hook(self, hook):
    """Set callback to invoke when asynchronous operation completes"""
    assert not self.done()
    assert callable(hook)
    self._hooks.append(hook)

  def _call_hooks(self):
    """Call hook functions, if present"""
    assert self.done()
    for hook in self._hooks:
      hook()


class ConnectOp(AsynchOp):
  def start(self, reactor, sock, addr):
    try:
      sock.connect(addr)
    except socket.error, why:
      self.error = why
    else:
      self.error = None

    if self.done():
      self._call_hooks()
    else:
      reactor._register_writable(self, sock)

  def done(self):
    return not self.error or self.error[0] != errno.EINPROGRESS


  def _notify(self, sock):
    assert not self.done()

    ### The getsockopt call may not be portable, esp to older unixes
    ### see http://cr.yp.to/docs/connect.html and
    ### http://www.muq.org/~cynbe/ref/nonblocking-connects.html
    ### for workarounds
    self.error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)

    if self.done():
      self._call_hooks()
      return False
    else:
      return True


class RecvOp(AsynchOp):
  def start(self, reactor, sock, bytes):
    self.recieved = None
    self.error = None
    reactor._register_readable(self, sock)
    self._bytes = bytes

  def done(self):
    return self.recieved is not None or self.error is not None

  def _notify(self, sock):
    assert not self.done()

    try:
      self.recieved = sock.recv(self._bytes)
    except socket.error, why:
      if why[0] == error.EWOULDBLOCK:
        return True
      else:
        self.error = why

    assert self.done()
    self._call_hooks()
    return False


class SendOp(AsynchOp):
  def start(self, reactor, sock, data):
    self.bytes_sent = None
    self.error = None
    reactor._register_writable(self, sock)
    self._data = data

  def done(self):
    return self.bytes_sent is not None or self.error is not None

  def _notify(self, sock):
    assert not self.done()

    try:
      self.bytes_sent = sock.send(self._data)
    except socket.error, why:
      if why[0] == error.EWOULDBLOCK:
        return True
      else:
        self.error = why

    assert self.done()
    self._call_hooks()
    return False


class Reactor:
  def __init__(self):
    self._reads = []
    self._writes = []
    self._readable_ops = {}
    self._writable_ops = {}

  def prep_socket(self, sock):
    # Get socket ready for use with the reactor. The current reactor
    # implemention doesn't really need sockets to be prepared using this call,
    # it'll work with any nonblocking socket, but I want to make possible
    # alternate implementations of Reactor using the same interface which
    # might need to prepare sockets differently. For example, an interface
    # that uses NT completion ports could call CreateIoCompletionPort to
    # associate a socket with the port
    sock.setblocking(False)

  def _register_readable(self, op, sock):
    self._reads.append(sock)
    try:
      ops = self._readable_ops[sock]
    except KeyError:
      self._readable_ops[sock] = [op]
    else:
      ops.append(op)

  def _register_writable(self, op, sock):
    self._writes.append(sock)
    try:
      ops = self._writable_ops[sock]
    except KeyError:
      self._writable_ops[sock] = [op]
    else:
      ops.append(op)

  def run(self, main_op):
    while main_op.kick() or not main_op.done():
      reads, writes, exceptions = select.select(self._reads, self._writes, [])

      for sock in reads:
        ops = self._readable_ops[sock]
        for op in ops:
          if not op._notify(sock):
            ops.remove(op)
        if not ops:
          self._reads.remove(sock)
          del self._readable_ops[sock]

      for sock in writes:
        ops = self._writable_ops[sock]
        for op in ops:
          if not op._notify(sock):
            ops.remove(op)
        if not ops:
          self._writes.remove(sock)
          del self._writable_ops[sock]

      assert not exceptions

class Fiber(AsynchOp):
  def start(self, *arg, **kwargs):
    self.generator = self._run(*arg, **kwargs)

  def _run(self, *arg, **kwargs):
    """Wrapper around user-defined run() that cleans up afterwards"""
    for w in self.run(*arg, **kwargs):
      yield w
    # Explicitly set generator to None in case any of the hooks want to 
    # call done()
    self.generator = None
    self._call_hooks()

  def run(self, *arg, **kwargs):
    """To be implemented by subclasses as a generator method"""
    raise NotImplementedError

  def wait(self, *op_sets):
    """Generator that doesn't return until operations have completed

    A variable number of operations can be passed as arguments, causing wait
    to return when ANY ONE of the operations has completed.

    Lists of operations can also be passed as arguments, causing wait to return
    when ALL the operations in ANY ONE of the lists have completed.

    In this way, wait() is fully general and can be made to wait for any
    combination of operations to complete.

    Examples:
      # wait for read operation OR timeout to complete
      wait(read, timeout)

      # wait for read AND write operations to complete
      wait((read, write))

      # wait for read AND write operations, OR timeout operation
      wait((read, write), timeout)
    """
    wait_any = []
    for op_set in op_sets:
      wait_all = []
      for op in not is_sequence(op_set) and (op_set, ) or op_set:
        if op and not op.done():
          wait_all.append(op)
          op.add_hook(lambda: wait_all.remove(op))
      wait_any.append(wait_all)

    while wait_any:
      for wait_all in wait_any:
        for op in wait_all:
          op.kick()
        if not wait_all:
          return
      yield None

  def done(self):
    return not self.generator

  def kick(self):
    try:
      self.generator.next()
    except StopIteration:
      pass


class SendAll(Fiber):
  def run(self, reactor, sock, buffer):
    self.bytes_sent = 0
    self.error = None

    while buffer:
      send = SendOp(reactor, sock, buffer)
      for w in self.wait(send):
        yield w

      if send.error is not None:
        self.error = send.error
        break

      self.bytes_sent += send.bytes_sent
      buffer = buffer[send.bytes_sent:]


def is_sequence(seq):
  try:
    iter(seq)
  except TypeError:
    return False
  return True

############

#SAT_ADDR = ('203.110.192.17', 23)
TIMEOUT = 1.0

class GetHttp(Fiber):
  def run(self, reactor, addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = ConnectOp(reactor, sock, addr)
    for w in self.wait(conn):
      yield w

    send = SendOp(reactor, sock, 'GET / HTTP/1.0\r\n\r\n')
    for w in self.wait(send):
      yield w
    print "-%i %i" % (addr[1], send.bytes_sent)

    while True:
      recv = RecvOp(reactor, sock, 100)
      for w in self.wait(recv):
        yield w
      if recv.error:
        print "RECV ERROR", read.error
      elif recv.recieved:
        print "+%i '%s'" % (addr[1], recv.recieved)
      else:
        print "=%i DONE" % addr[1]
        break
    sock.close()

class Test(Fiber):
  def run(self, reactor):
    page1 = GetHttp(reactor, ('10.0.0.1', 8001))
    page2 = GetHttp(reactor, ('10.0.0.1', 8002))
    for w in self.wait(page1, page2):
      yield w

def main():
  reactor = Reactor()
  reactor.run(Test(reactor))
  #reactor.run(GetHttp(reactor, ('10.0.0.1',8003)))

if __name__ == '__main__':
  main()
