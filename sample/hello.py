import logging
import squall
from squall import coroutine
squall.configLogger(logging.DEBUG)


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


    hello("Ivan", 2.0)
    hello("Alesh", 3.0)
    hello("World", 5.0)
    terminate(11.0)
    squall.start()
