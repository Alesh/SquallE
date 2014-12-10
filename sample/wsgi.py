import squall
from squall.scgi2wsgi import wsgi
from squall.utilites import configLogger


def application(environ, start_responce):
    start_responce("200 OK", [("Content-Type", "text/plain; charset=UTF-8")])
    for name, value in environ.items():
        yield "{}:\t{}\r\n".format(name, value).encode("UTF-8")


if __name__ == '__main__':
    import logging
    configLogger(logging.INFO)
    squall.streamServer(wsgi(application), ("127.0.0.1", 7000), 64)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()