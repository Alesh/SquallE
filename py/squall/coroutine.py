"""`squall.coroutine`"""
import functools
from collections import deque
from squall.utilites import log
from squall.dispatcher import dispatcher
from squall.dispatcher import READ, WRITE, TIMEOUT, IDLE


class CoroAPI(type):
    """The coroutine metaclass and API container."""
    def __init__(cls, *args):
        cls._all = dict()
        cls._current = deque()
        super(CoroAPI, cls).__init__(*args)

    @property
    def all(cls):
        """Handles of all active coroutines."""
        return tuple(cls._all.keys())

    @property
    def current(cls):
        """Handle of current coroutine."""
        return id(cls._current[0]) if len(cls._current) else None

    @property
    def dispatcher(cls):
        """Event dispatcher."""
        return dispatcher

    def sleep(cls, timeout=None):
        """Pauses current coroutine until timeout is not expired."""
        # callback resume coroutine and sent to it revents
        def resume(handle, revents):
            coroutine.switch(handle, revents)
        assert cls.current is not None, "Can called only from coroutine."
        callback = functools.partial(resume, coroutine.current)
        timeout = timeout or 0
        if timeout > 0:
            dispatcher.watch(callback, timeout=timeout)
        else:
            dispatcher.call(callback)
        return (yield)

    def wait(cls, fd, eventmask, timeout=None):
        """Pauses current coroutine until event is not occurred."""
        # callback resume coroutine and sent to it revents
        def resume(handle, revents):
            coroutine.switch(handle, revents)
        assert cls.current is not None, "Can called only from coroutine."
        callback = functools.partial(resume, coroutine.current)
        dispatcher.watch(callback, fd, eventmask, timeout or 0)
        return (yield)

    def switch(cls, handle, value):
        """Switches to coroutine by handle and send value."""
        with context(handle) as corogen:
            corogen.send(value)

    def throw(cls, handle, exception):
        """Switches to coroutine by handle and raise given exception."""
        with context(handle) as corogen:
            corogen.throw(exception)


class coroutine(metaclass=CoroAPI):
    """Makes coroutine from a function or method."""
    def __init__(self, run):
        self._obj = None
        self._run = run

    def __get__(self, obj, cls):
        self._obj = obj

    def __call__(self, *args, **kwargs):
        # calback starts coroutine
        def start(handle, revents):
            assert revents == IDLE
            with context(handle) as corogen:
                log.debug("Coroutine with handle: {:X} has started.".format(handle))
                next(corogen)
        run = functools.partial(self._run, self._obj) if self._obj else self._run
        corogen = run(*args, **kwargs)
        handle = id(corogen)
        coroutine._all[handle] = corogen
        dispatcher.call(functools.partial(start, handle))
        return handle


class context(object):
    """Current coroutine context."""
    def __init__(self, handle):
        if handle in coroutine._all:
            self.corogen = coroutine._all[handle]
        else:
            raise ValueError("Cannot found coroutine for given handle.")

    def __enter__(self):
        coroutine._current.appendleft(self.corogen)
        return self.corogen

    def __exit__(self, type, value, traceback):
        handle = coroutine.current
        coroutine._current.popleft()
        if type is not None:
            if type == StopIteration or type == GeneratorExit:
                log.debug("Coroutine with handle: {:X} has terminated.".format(handle))
            else:
                try:
                    raise value.with_traceback(traceback)
                except:
                    log.exception("Coroutine with handle: {:X} has terminated because uncaught exception:".format(handle))
            del coroutine._all[handle]
        return True


def start():
    """Starts event dispatching."""
    try:
        dispatcher.start()
    except KeyboardInterrupt:
        pass
    finally:
        dispatcher.stop()
        for handle in coroutine.all:
            coroutine.throw(handle, GeneratorExit)


def stop():
    """Stops event dispatching."""
    dispatcher.stop()
