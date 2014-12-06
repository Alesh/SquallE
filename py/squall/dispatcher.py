"""`squall.dispatcher`"""

import selectors
import functools
from collections import deque
from time import sleep, time as now
from heapq import heappush, heappop
from squall.utilites import Singleton


READ = selectors.EVENT_READ
WRITE = selectors.EVENT_WRITE
TIMEOUT = 0x20
IDLE = 0x40
CLEANUP = 0x80


class Dispatcher(metaclass=Singleton):
    """The event dispatcher."""

    def __init__(self):
        self._started = False
        self._idles = deque()
        self._timeouts = list()
        self._selector = selectors.DefaultSelector()

    def call(self, callback, not_once=False):
        """Setups the next idle callback."""
        self._idles.append(callback)

    def watch(self, callback, fileobj=None, eventmask=None, timeout=None):
        """Setups the event watcher."""
        assert (fileobj is not None and eventmask is not None) or timeout is not None
        deadline = now() + timeout if timeout > 0 else None
        if deadline is not None:
            heappush(self._timeouts, (deadline, fileobj, callback))
        if fileobj is not None:
            self._selector.register(fileobj, eventmask, (callback, deadline))

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
        if len(self._selector.get_map()):
            polled = self._selector.select(timeout)
            # process polled
            for key, eventmask in polled:
                fileobj = key.fileobj
                callback, deadline = key.data
                if deadline is not None:
                    self._timeouts.remove((deadline, fileobj, callback))
                self._selector.unregister(fileobj)
                callback(eventmask)
        else:
            sleep(timeout)
        # process timed out
        while len(self._timeouts):
            deadline, fileobj, callback = heappop(self._timeouts)
            if deadline < now():
                if fileobj is not None:
                    self._selector.unregister(fileobj)
                callback(TIMEOUT)
            else:
                heappush(self._timeouts, (deadline, fileobj, callback))
                break

    def start(self):
        """Starts the event loop."""
        self._started = True
        while self._started and (len(self._timeouts) or len(self._idles) or len(self._selector.get_map())):
            self.loop()
        self._started = False

    def stop(self):
        """Stops the event loop."""
        self._started = False


# Default dispatcher
dispatcher = Dispatcher()
