import squall
from squall import coroutine


@coroutine
def hello(name, timeout):
    while True:
        yield from coroutine.sleep(timeout)
        print("Hello, {}!".format(name))


@coroutine
def terminate(timeout):
    yield from coroutine.sleep(timeout)
    squall.stop()


if __name__ == '__main__':

    import logging
    from squall.utilites import configLogger
    configLogger(logging.WARNING)

    hello("Ivan", 2.0)
    hello("Alesh", 3.0)
    hello("World", 5.0)
    terminate(11.0)
    squall.start()
