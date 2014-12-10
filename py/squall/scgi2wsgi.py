"""`squall.scgi2wsgi`"""
import io
import errno
import collections
from squall.network import stream
from squall.coroutine import coroutine
from squall.utilites import log, timeout_gen


class ErrorStream(object):
    """WSGI error stream adapter."""
    def write(self, msg):
        log.error(msg)

    def writelines(self, seq):
        for msg in seq:
            log.error(msg)

    def flush(self):
        pass


class InputStream(io.BytesIO):
    """WSGI input stream adapter."""
    def __init__(self, environ, timeout):
        self._timeout = timeout
        self._content_length = int(environ.get('CONTENT_LENGTH', '0'))
        environ['squall.async_body_loader'] = self._async_body_loader
        super(InputStream, self).__init__()

    def _async_body_loader(self, callback=None):
            remained = self._content_length
            callback = callback or (lambda current, total: True)
            while remained > 0:
                block_size = stream.chunk_size if stream.chunk_size < remained else remained
                data = yield from stream.read(block_size, next(self._timeout))
                remained -= len(data)
                if callback(self._content_length-remained, self._content_length):
                    self.write(data)
            self.seek(0)

class Gateway(type):
    """SCGI2WSGI Gateway API hub"""
    def __init__(cls, *args):
        cls._state = dict()
        super(Gateway, cls).__init__(*args)

    @property
    def _headers_sent(cls):
        handle = coroutine.current
        return cls._state[handle][0] if handle is not None else None

    @_headers_sent.setter
    def _headers_sent(cls, value):
        handle = coroutine.current
        if handle is not None:
            cls._state[handle][0] = value
        else:
            raise AttributeError

    @property
    def _out_headers(cls):
        handle = coroutine.current
        return cls._state[handle][1] if handle is not None else None

    @property
    def _out_buffer(cls):
        handle = coroutine.current
        return cls._state[handle][2] if handle is not None else None

    @_out_buffer.setter
    def _out_buffer(cls, value):
        handle = coroutine.current
        if handle is not None:
            cls._state[handle][2] = value
        else:
            raise AttributeError

    @property
    def chunk_size(cls):
        """Buffer chunk size of current stream."""
        handle = coroutine.current
        return cls._state[handle][3] if handle is not None else None

    @property
    def buffer_size(cls):
        """Buffer size of current stream."""
        handle = coroutine.current
        return cls._state[handle][4] if handle is not None else None

    @property
    def _default_environ(cls):
        return {
            'wsgi.version': (1, 0),
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': True,
        }

    def _read_environ(cls, input_async, timeout):
        timeout = timeout_gen(timeout)
        data = yield from stream.readUntil(b':', 12, next(timeout))
        if data[-1] != 58:
            raise ValueError("Wrong SCGI header size")
        data = yield from stream.read(int(data[:-1])+1, next(timeout))
        if data[-1] != 44:
            raise ValueError("Wrong SCGI header")
        environ = dict(cls._default_environ)
        parts = [part.decode('iso-8859-1') for part in data[:-1].split(b"\000")]
        environ.update(dict(zip(parts[0::2], parts[1::2])))
        environ['wsgi.errors'] = ErrorStream()
        environ['wsgi.input'] = InputStream(environ, timeout)
        if 'PATH_INFO' not in environ:
            if 'SCRIPT_NAME' not in environ:
                environ['PATH_INFO'] = environ['REQUEST_URI']
            else:
                environ['PATH_INFO'] = environ['REQUEST_URI'].split(environ['SCRIPT_NAME'])[1]
                environ['PATH_INFO'] = environ['PATH_INFO'] or '/'
        if environ.get('HTTPS', 'off') in ('on', '1'):
            environ['wsgi.url_scheme'] = 'https'
        else:
            environ['wsgi.url_scheme'] = 'http'

        if not input_async:
            yield from environ['squall.async_body_loader']()
            del environ['squall.async_body_loader']
        return environ

    def _start_response(cls, status, response_headers, exc_info=None):
        if exc_info:
            try:
                if cls._headers_sent:
                    raise exc_info[1].with_traceback(exc_info[2])
            finally:
                exc_info = None
        elif cls._out_headers:
            raise AssertionError("Headers already set!")
        cls._out_headers.append(('Status', status))
        for name, value in response_headers:
            cls._out_headers.append((name, value))

    def _out_head(cls):
        if not cls._headers_sent:
            for name, value in cls._out_headers:
                yield from cls._write('{}: {}\r\n'.format(name, value).encode('iso-8859-1'))
            yield from cls._write(b'\r\n', True)
            cls._headers_sent = True

    def _out_generator(cls, app_iter):
        try:
            chunk = next(app_iter)
            while True:
                if chunk is None:
                    event = yield
                else:
                    event = None
                    if not cls._headers_sent:
                        yield from cls._out_head()
                    if not isinstance(chunk, bytes):
                        raise ValueError("WSGI Application return wrong type of app_iter items: {}".format(type(chunk)))
                    yield from cls._write(chunk)
                chunk = app_iter.send(event)
        except StopIteration as exc:
            if exc.value:
                if hasattr(exc.value, 'send'):
                    yield from cls._out_generator(exc.value)
                else:
                    yield from cls._out_response(exc.value)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()

    def _out_response(cls, app_iter):
        if hasattr(app_iter, 'send'):
            yield from cls._out_generator(app_iter)
        else:
            if isinstance(app_iter, bytearray):
                app_iter = bytes(app_iter)
            if isinstance(app_iter, bytes):
                app_iter = [app_iter]
            elif not hasattr(app_iter, '__iter__'):
                raise ValueError("WSGI Application return wrong type of app_iter: {}".format(type(app_iter)))
            if not cls._headers_sent:
                yield from cls._out_head()
            for chunk in app_iter:
                if not isinstance(chunk, bytes):
                    raise ValueError("WSGI Application return wrong type of app_iter items")
                yield from cls._write(chunk)
            if hasattr(app_iter, 'close'):
                app_iter.close()

    def _write(cls, data=b'', flush=False):
        flush = flush if cls.buffer_size > 0 else True
        buffer_size = cls.buffer_size or cls.chunk_size * 8
        max_buffer_size = buffer_size * 4
        if (len(cls._out_buffer)+len(data)) > max_buffer_size:
            raise OSError(errno.ENOBUFS, "No buffer space available.")
        cls._out_buffer += data
        if len(cls._out_buffer) == 0:
            return
        # send
        countdown = 8
        while countdown > 0:
            if flush:
                while (countdown > 0) and len(cls._out_buffer):
                    sent = yield from stream.write(cls._out_buffer[:cls.chunk_size])
                    if sent:
                        cls._out_buffer = cls._out_buffer[sent:]
                        countdown = 8
                    else:
                        countdown -= 1
                break
            else:
                while (countdown > 0) and (len(cls._out_buffer) > buffer_size):
                    sent = yield from stream.write(cls._out_buffer[:cls.chunk_size])
                    if sent:
                        cls._out_buffer = cls._out_buffer[sent:]
                        countdown = 8
                    else:
                        countdown -= 1
                break
        if countdown == 0:
            raise OSError(errno.ECOMM, "Cannot send response.")

    def _init_instance(cls, handle, chunk_size, buffer_size):
        chunk_size = chunk_size if chunk_size > 1024 else 1024
        chunk_size = chunk_size if chunk_size < 64*1024 else 64*1024
        cls._state[handle] = [False, [], b'', chunk_size, buffer_size]

    def _release_instance(cls, handle):
        del cls._state[handle]



class wsgi(metaclass=Gateway):
    """Makes application coroutine from a function or method."""
    def __init__(self, run=None, chunk_size=None, buffer_size=None, timeout=None, input_async=False):
        self._run = run
        self._obj = self._coro = None
        self.timeout = timeout
        self.input_async = input_async
        self.chunk_size = chunk_size or 4*1024
        self.buffer_size = buffer_size if buffer_size is not None else 256*1024
        super(wsgi, self).__init__()


    def __get__(self, obj, cls):
        self._obj = obj

    def __call__(self, *args, **kwargs):
        if self._run is not None:
            application = functools.partial(self._run, self._obj) if self._obj else self._run
            if self._coro is None:
                # application coroutine wrapper
                def wrapper(address):
                    handle = coroutine.current
                    wsgi._init_instance(handle, self.chunk_size, self.buffer_size)
                    environ = yield from wsgi._read_environ(self.input_async, self.timeout)
                    yield from wsgi._out_response(application(environ, wsgi._start_response))
                    if not wsgi._headers_sent:
                        yield from wsgi._out_head()
                    else:
                        yield from wsgi._write(flush=True)
                    wsgi._release_instance(handle)
                self._coro = stream(wrapper, self.chunk_size, self.buffer_size)
            return self._coro(*args, **kwargs)
        else:
            self._run = args[0]
            return self
