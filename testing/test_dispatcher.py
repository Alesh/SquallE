from time import time
from squall.dispatcher import dispatcher, Dispatcher, TIMEOUT


def test_singleton():
    dispA = Dispatcher()
    dispB = Dispatcher()
    assert dispA == dispB
    assert dispatcher == dispA


def test_timeouts():
    result = list()
    dispatcher = Dispatcher()
    dispatcher.watch(lambda ev: result.append((0.1, ev)), timeout=0.1)
    dispatcher.watch(lambda ev: result.append((0.5, ev)), timeout=0.5)
    dispatcher.watch(lambda ev: result.append((0.3, ev)), timeout=0.3)
    start_at = time()
    dispatcher.start()
    seconds = time()-start_at
    assert seconds <= 0.51 and seconds >= 0.5
    assert result == [(0.1, TIMEOUT), (0.3, TIMEOUT), (0.5, TIMEOUT)]



if __name__ == '__main__':
    test_singleton()
    test_timeouts()
