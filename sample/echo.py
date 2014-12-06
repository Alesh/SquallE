import squall
from squall import stream, streamServer
from squall.utilites import log, configLogger

@stream
def echo(address):
    try:
        log.info("Accepted connection from: {}.".format(address))
        while True:
            ## data = yield from stream.readLine(timeout=15)
            data = yield from stream.readUntil(b'\r\n\r\n', timeout=15) ##
            if data:
                yield from stream.write(data)
                break ##
                continue
            log.info("Connection from: {} reset by peer.".format(address))
            break
    except TimeoutError:
        log.info("Connection from: {}  reset by timeout.".format(address))


if __name__ == '__main__':
    import logging
    configLogger(logging.WARNING)
    streamServer(echo, ("127.0.0.1", 2007), 64)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()
