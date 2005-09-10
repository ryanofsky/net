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
    try:
      ops = self._readable_ops[sock]
    except KeyError:
      self._readable_ops[sock] = [op]
      self._reads.append(sock)
    else:
      ops.append(op)

  def _register_writable(self, op, sock):
    try:
      ops = self._writable_ops[sock]
    except KeyError:
      self._writable_ops[sock] = [op]
      self._writes.append(sock)
    else:
      ops.append(op)

  def run(self, main_op):
    while not main_op.done():
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
    self._kick()

  def run(self, *arg, **kwargs):
    """To be implemented by subclasses as a generator method

    The generator can yield operations or sequences of operations and it
    will be automatically resumed when the operations complete. If it
    yields a sequence of operations, it will be resumed when ANY ONE of the
    operations completes. If it yields a sequence of subsequences of
    operations, it will resume when ALL of the operations in ANY ONE of the
    subsequences completes.

    Examples:
      # wait for read operation OR timeout to complete
      yield (read, timeout)

      # wait for read AND write operations, OR timeout operation
      yield ((read, write), timeout)
    
      # wait for read AND write operations to complete
      yield ((read, write),)

    In this way, the resume mechanism is fully general and a fiber can
    for any combination of operations to complete.
    """
    raise NotImplementedError

  def _run(self, *arg, **kwargs):
    """Wrapper around user-defined run() that cleans up afterwards"""
    for op_sets in self.run(*arg, **kwargs):
      if self._add_hooks(op_sets):
        yield None
    # Explicitly set generator to None in case any of the hooks want to 
    # call done()
    self.generator = None
    self._call_hooks()

  def _add_hooks(self, op_sets):
    """Add hooks to resume Fiber when specified operations complete"""
    for op_set in isinstance(op_sets, AsynchOp) and (op_sets,) or op_sets:
      wait_all = []
      for op in isinstance(op_set, AsynchOp) and (op_set,) or op_set:
        if not op.done():
          wait_all.append(op)
          def hook(wait_all=wait_all, op=op):
            wait_all.remove(op)
            if not wait_all:
              self._kick()
          op.add_hook(hook)
      if not wait_all:
        return False
    return True

  def done(self):
    return not self.generator

  def _kick(self):
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
      yield send

      if send.error is not None:
        self.error = send.error
        break

      self.bytes_sent += send.bytes_sent
      buffer = buffer[send.bytes_sent:]


############

#SAT_ADDR = ('203.110.192.17', 23)
TIMEOUT = 1.0

class GetHttp(Fiber):
  def run(self, reactor, addr):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    yield ConnectOp(reactor, sock, addr)

    send = SendOp(reactor, sock, 'GET / HTTP/1.0\r\n\r\n')
    yield send
    print "-%i %i" % (addr[1], send.bytes_sent)

    while True:
      recv = RecvOp(reactor, sock, 100)
      yield recv
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
    yield (page1, page2),

def main():
  reactor = Reactor()
  reactor.run(Test(reactor))
  #reactor.run(GetHttp(reactor, ('10.0.0.1',8003)))

if __name__ == '__main__':
  main()
