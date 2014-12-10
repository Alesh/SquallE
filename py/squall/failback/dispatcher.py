"""`squall.dispatcher`"""

import select
import functools
from collections import deque
from time import time as now
from heapq import heappush, heappop
from squall.utilites import Singleton


class Poll(object):
    """Poll object."""
    READ = select.EPOLLIN                      # 0b0000000000000001
    WRITE = select.EPOLLOUT                    # 0b0000000000000100
    ERROR = select.EPOLLERR | select.EPOLLHUP  # 0b0000000000011000

    def __init__(self):
        self._impl = select.epoll()

    def register(self, fd, eventmask):
        return self._impl.register(fd, eventmask)

    def unregister(self, fd):
        return self._impl.unregister(fd)

    def poll(self, timeout):
        return self._impl.poll(timeout)


READ = Poll.READ
WRITE = Poll.WRITE
ERROR = Poll.ERROR
TIMEOUT = 0x20
IDLE = 0x40
CLEANUP = 0x80


class Dispatcher(metaclass=Singleton):
    """The event dispatcher."""

    def __init__(self):
        self._poll = Poll()
        self._started = False
        self._idles = deque()
        self._pending = dict()
        self._timeouts = list()

    def call(self, callback, not_once=False):
        """Setups the next idle callback."""
        self._idles.append(callback)

    def watch(self, callback, fd=None, eventmask=None, timeout=None):
        """Setups the event watcher."""
        assert (fd is not None and eventmask is not None) or timeout is not None
        deadline = now() + timeout if timeout > 0 else None
        if deadline is not None:
            heappush(self._timeouts, (deadline, fd, callback))
        if fd is not None:
            self._poll.register(fd, eventmask)
            self._pending[fd] = (callback, deadline)

    def loop(self):
        """Performs one event loop."""
        # process idle callbacks
        idles = deque(self._idles)
        self._idles.clear()
        while len(idles):
            callback = idles.popleft()
            callback(IDLE)
        # polling
        if len(self._timeouts):
            deadline, _a, _b = heappop(self._timeouts)
            heappush(self._timeouts, (deadline, _a, _b))
        else:
            deadline = None
        timeout = deadline - now() if deadline is not None else 3600.0
        timeout = timeout if timeout > 0 else 0

        polled = self._poll.poll(timeout)
        # process polled
        for fd, eventmask in polled:
            callback, deadline = self._pending.pop(fd)
            if deadline is not None:
                self._timeouts.remove((deadline, fd, callback))
            self._poll.unregister(fd)
            callback(eventmask)
        # process timed out
        while len(self._timeouts):
            deadline, fd, callback = heappop(self._timeouts)
            if deadline < now():
                if fd is not None:
                    self._pending.pop(fd)
                    self._poll.unregister(fd)
                callback(TIMEOUT)
            else:
                heappush(self._timeouts, (deadline, fd, callback))
                break

    def start(self):
        """Starts the event loop."""
        self._started = True
        while self._started and (len(self._timeouts) or len(self._idles) or len(self._pending)):
            self.loop()
        self._started = False

    def stop(self):
        """Stops the event loop."""
        self._started = False


# Default dispatcher
dispatcher = Dispatcher()
