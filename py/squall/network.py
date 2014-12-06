"""`squall.network`"""
import errno
import socket
from time import time as now
from squall.utilites import log, timeout_gen
from squall.coroutine import coroutine, READ, WRITE, TIMEOUT


class StreamAPI(type):
    """Stream API hub"""
    def __init__(cls, *args):
        cls._ci = dict()
        super(StreamAPI, cls).__init__(*args)

    @property
    def _socket(cls):
        handle = coroutine.current
        return cls._ci[handle][0] if handle is not None else None

    @property
    def _in_buffer(cls):
        handle = coroutine.current
        return cls._ci[handle][1] if handle is not None else None

    @_in_buffer.setter
    def _in_buffer(cls, value):
        handle = coroutine.current
        if handle is not None:
            cls._ci[handle][1] = value
        else:
            raise AttributeError

    @property
    def _out_buffer(cls):
        handle = coroutine.current
        return cls._ci[handle][2] if handle is not None else None

    @_out_buffer.setter
    def _out_buffer(cls, value):
        handle = coroutine.current
        if handle is not None:
            cls._ci[handle][2] = value
        else:
            raise AttributeError

    @property
    def chunk_size(cls):
        """Chunk size of current stream."""
        handle = coroutine.current
        return cls._ci[handle][3] if handle is not None else None

    @property
    def buffer_size(cls):
        """Buffer size of current stream."""
        handle = coroutine.current
        return cls._ci[handle][4] if handle is not None else None

    @property
    def EOF(cls):
        """Returnf True if current stream EOF."""
        handle = coroutine.current
        return cls._ci[handle][5] if handle is not None else None

    def _set_eof(cls, value):
        handle = coroutine.current
        if handle is not None:
            cls._ci[handle][5] = value

    def _fill_in_buff(cls, socket, timeout, chunk_size, buffer_size):
        revents = yield from coroutine.wait(socket, READ, next(timeout))
        if revents & READ:
            block_size = buffer_size - len(cls._in_buffer)
            block_size = block_size if block_size < chunk_size else chunk_size
            received = socket.recv(block_size)
            if received:
                cls._in_buffer += received
            else:
                cls._set_eof(True)
        elif revents & TIMEOUT:
            raise OSError(errno.ETIMEDOUT, "Connection timed out.")

    def read(cls, number=None, timeout=None):
        """Read a number of bytes from current stream."""
        assert coroutine.current in cls._ci
        if cls.EOF:
            raise OSError(errno.ECONNRESET, "Connection was reset.")
        data = b''
        buffer_size = cls.buffer_size
        timeout = timeout_gen(timeout)
        number = number or buffer_size
        number = number if number < buffer_size else buffer_size
        while not cls.EOF:
            if number <= len(cls._in_buffer):
                data = cls._in_buffer[:number]
                cls._in_buffer = cls._in_buffer[number:]
                break
            yield from cls._fill_in_buff(cls._socket, timeout, cls.chunk_size, buffer_size)
        else:
            data = cls._in_buffer
            cls._in_buffer = b''
        return data

    def readUntil(cls, delimiter, max_number=None, timeout=None):
        """Read bytes from current stream until we have found the delimiter."""
        assert coroutine.current in cls._ci
        if cls.EOF:
            raise OSError(errno.ECONNRESET, "Connection was reset.")
        data = b''
        buffer_size = cls.buffer_size
        timeout = timeout_gen(timeout)
        max_number = max_number or buffer_size
        max_number = max_number if max_number < buffer_size else buffer_size
        while not cls.EOF:
            pos = cls._in_buffer.find(delimiter)
            if pos >= 0:
                pos += len(delimiter)
                data = cls._in_buffer[:pos]
                cls._in_buffer = cls._in_buffer[pos:]
                break
            if max_number <= len(cls._in_buffer):
                data = cls._in_buffer[:max_number]
                cls._in_buffer = cls._in_buffer[max_number:]
                break
            yield from cls._fill_in_buff(cls._socket, timeout, cls.chunk_size, buffer_size)
        else:
            data = cls._in_buffer
            cls._in_buffer = b''
        return data

    def readLine(cls, max_number=None, timeout=0):
        """Read line bytes from current stream terminated with LF."""
        return (yield from cls.readUntil(b'\n', max_number, timeout))

    def write(cls, data, timeout=None):
        """Write bytes to current stream."""
        assert coroutine.current in cls._ci
        chunk_size = cls.chunk_size
        buffer_size = cls.buffer_size
        timeout = timeout_gen(timeout)
        can_sent = buffer_size - len(cls._out_buffer)
        can_sent = can_sent if len(data) > can_sent else len(data)
        cls._out_buffer += data[:can_sent]
        while len(cls._out_buffer):
            revents = yield from coroutine.wait(cls._socket, WRITE, next(timeout))
            if revents & WRITE:
                block_size = chunk_size if chunk_size < len(cls._out_buffer) else len(cls._out_buffer)
                sent = cls._socket.send(cls._out_buffer[:block_size])
                cls._out_buffer = cls._out_buffer[block_size:]
            elif revents & TIMEOUT:
                raise OSError(errno.ETIMEDOUT, "Connection timed out.")
        return can_sent


class stream(metaclass=StreamAPI):
    """Makes stream coroutine from a function or method."""
    def __init__(self, run=None, chunk_size=None, buffer_size=None):
        self._run = run
        self._obj = self._coro = None

        chunk_size = chunk_size or 4096
        chunk_size = chunk_size if chunk_size > 1024 else 1024
        self.chunk_size = chunk_size if chunk_size < 64*1024 else 64*1024

        buffer_size = buffer_size or 262144
        buffer_size = buffer_size if buffer_size > 1024*8 else 1024*8
        self.buffer_size = buffer_size if buffer_size < chunk_size*8 else chunk_size*8

        super(stream, self).__init__()

    def __get__(self, obj, cls):
        self._obj = obj

    def __call__(self, *args, **kwargs):
        if self._run is not None:
            run = functools.partial(self._run, self._obj) if self._obj else self._run
            if self._coro is None:
                # stream coroutine wrapper
                def wrapper(client_socket, address):
                    handle = coroutine.current
                    client_socket.setblocking(False)
                    stream._ci[handle] = [client_socket, b'', b'', self.chunk_size, self.buffer_size, False]
                    log.debug("Accepted connection from: {}.".format(address))
                    try:
                        yield from run(address)
                    finally:
                        del stream._ci[handle]
                        client_socket.shutdown(socket.SHUT_RDWR)
                        client_socket.close()
                        log.debug("Closed connection from: {}.".format(address))
                self._coro = coroutine(wrapper)
            return self._coro(*args, **kwargs)
        else:
            self._run = args[0]
            return self


@coroutine
def acceptor(coroinst, server_socket):
    log.info("Established listener on: {}.".format(server_socket.getsockname()))
    try:
        while True:
            revents = yield from coroutine.wait(server_socket.fileno(), READ)
            if revents & READ:
                client_socket, address = server_socket.accept()
                coroinst(client_socket, address)
    finally:
        log.debug("Finished listener on: {}.".format(server_socket.getsockname()))
        server_socket.close()


def streamServer(coroinst, address, backlog):
    """Starts TCP server."""
    result = list()
    host, port = address
    addrinfo = socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                  socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
    for family, socktype, proto, _, addr in addrinfo:
        # create socket
        try:
            server_socket = socket.socket(family, socktype, proto)
        except OSError as exc:
            log.warning("Cannot create server socket: {}.".format((family, socktype, proto)))
            server_socket = None
            continue
        # bind and setup socket
        try:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(addr)
            server_socket.listen(backlog)
        except OSError as exc:
            log.warning("Cannot setup server socket: {}.".format((family, socktype, proto, addr)))
            server_socket.close()
            server_socket = None
            continue
        # create coroutine-acceptor
        try:
            handle = acceptor(coroinst, server_socket)
            result.append(handle)
        except Exception as exc:
            log.exception("Cannot create connection acceptor on: {}.", addr)
    if len(result) == 0:
        log.error("Cannot start server: {}.".format(address))
    return result
