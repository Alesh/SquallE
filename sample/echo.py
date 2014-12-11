import squall
import logging
from squall import coroutine, log, configLogger
from squall.failback.network import stream, streamServer


@stream
def echo(address):
    try:
        log.info("Accepted connection from: {}.".format(address))
        while True:
            data = yield from stream.readLine(timeout=15)
            if data:
                yield from stream.write(data)
                continue
            log.info("Connection from: {} reset by peer.".format(address))
            break
    except TimeoutError:
        log.info("Connection from: {} reset by timeout.".format(address))


@coroutine
def close_by(timeout):
    yield from coroutine.sleep(timeout)
    log.info("Too much of a good thing is good for nothing. Bye.")
    squall.stop()

if __name__ == '__main__':
    configLogger(logging.INFO)
    streamServer(echo, ("127.0.0.1", 2007), 64)
    close_by(60)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()
