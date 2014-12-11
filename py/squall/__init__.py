"""`squall`"""
# from squall.network import stream, streamServer
import squall.utilites
import squall.coroutine
from squall.coroutine import coroutine, log, start, stop
from squall.coroutine import READ, WRITE, IDLE, TIMEOUT


def configLogger(*arg, **kwargs):
    squall.utilites.config_logger(*arg, **kwargs)
    squall.coroutine.dispatcher.setup_logging(squall.utilites.log.getEffectiveLevel())
