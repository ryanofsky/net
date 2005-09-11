import cStringIO
import time
import socket
import select
import errno
import time


class AsynchOp:
  def __init__(self, *args, **kwargs):
    """Create instance and call start() if given arguments"""
    self._hook = None
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

  def set_hook(self, hook):
    """Set callback to invoke when asynchronous operation completes"""
    assert not self.done()
    assert ((callable(hook) and self._hook is None)
            or hook is None and callable(self._hook))
    self._hook = hook

  def _call_hook(self):
    """Call hook functions, if present"""
    assert self.done()
    if self._hook is not None:
      self._hook()


class ConnectOp(AsynchOp):
  def start(self, reactor, sock, addr):
    try:
      sock.connect(addr)
    except socket.error, why:
      self.error = why
    else:
      self.error = None

    if self.done():
      self._call_hook()
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
      self._call_hook()
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
    self._call_hook()
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
    self._call_hook()
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
    operations in the sequence completes. If it yields a sequence of
    subsequences of operations, it will resume when ALL of the operations in
    ANY ONE of the subsequences completes.

    Examples:
      # automatically resume generator when read operation completes
      yield read

      # resume when read operation OR timeout operation completes
      yield (read, timeout)

      # resume when read AND write operations, OR timeout operation completes
      yield ((read, write), timeout)

      # resume when read AND write operations completes
      yield ((read, write),)

    In this way, the resume mechanism is fully general and a fiber can
    for any combination of operations to complete."""
    raise NotImplementedError

  def _run(self, *arg, **kwargs):
    """Wrapper around run() that handles yield values and calls hook"""
    for op_sets in self.run(*arg, **kwargs):
      # Get fiber to automatically resume when yielded operations complete

      # if yield value is not a sequence, make it one
      if isinstance(op_sets, AsynchOp) or op_sets is None:
        op_sets = op_sets,

      # list of sublists of operations. operations remove themselves from
      # sublists as they complete and fiber resumes when ALL the operations
      # in ANY of the sublists are gone
      wait_any = []

      for op_set in op_sets:
        # if yielded sequence element is not a subsequence, make it one
        if isinstance(op_set, AsynchOp) or op_set is None:
          op_set = op_set,

        # sublist of operations. if empty, fiber resumes
        wait_all = []

        for op in op_set:
          if not op.done():
            # hook function called when op completes
            def hook(wait_any=wait_any, wait_all=wait_all, op=op, fiber=self):
              wait_all.remove(op)

              # if nothing left to wait for, remove any hooks and wake up fiber
              if not wait_all:
                for ops in wait_any:
                  for op in ops:
                    op.set_hook(None)
                fiber._kick()

            op.set_hook(hook)
            wait_all.append(op)

        # if set is empty, remove any hooks and resume fiber right away
        if wait_all:
          wait_any.append(wait_all)
        else:
          for ops in wait_any:
            for op in ops:
              op.set_hook(None)
          del wait_any[:]
          break

      # Go to sleep, will wake up when one of the operations the fiber
      # is waiting on completes and calls kick()
      if wait_any:
        yield None

    # Fiber has finished, call hooks, but first set generator to None in case
    # any of the hooks want to fiber.done()
    self.generator = None
    self._call_hook()

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
