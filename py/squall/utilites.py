"""`squall.utilites`"""

import logging
from time import time as now

log = logging.Logger("squall")
log.setLevel(logging.WARNING)


class Singleton(type):
    """Singleton"""
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instance


def configLogger(level=None, handler=None, formater=None):
    """Configs module logger with given parameters."""
    level = level or logging.DEBUG
    handler = handler or logging.StreamHandler()
    formater = formater or logging.Formatter('%(name)s: %(levelname)s: %(message)s')
    if level < log.getEffectiveLevel():
        log.setLevel(level)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formater)
    log.addHandler(handler)


def timeout_gen(timeout):
    """Timeout generator."""
    deadline = now()+timeout if timeout is not None else None
    while True:
        yield (None if deadline is None
               else (deadline - now() if deadline - now() > 0 else 0))
