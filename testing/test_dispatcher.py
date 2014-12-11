from time import time
from squall.coroutine import dispatcher, TIMEOUT
from squall.failback.dispatcher import dispatcher as fb_dispatcher
from squall.failback.dispatcher import Dispatcher as fb_Dispatcher


def test_singleton():
    dispA = fb_Dispatcher()
    dispB = fb_Dispatcher()
    assert dispA == dispB
    assert fb_dispatcher == dispA


def test_load_dispatcher():
    assert fb_dispatcher != dispatcher


def test_timeouts():
    result = list()
    assert dispatcher.watch(lambda ev: result.append((0.1, ev)), timeout=0.1)
    #assert dispatcher.watch(lambda ev: result.append((0.5, ev)), timeout=0.5)
    #assert dispatcher.watch(lambda ev: result.append((0.3, ev)), timeout=0.3)
    start_at = time()
    dispatcher.start()
    seconds = time()-start_at
    assert seconds <= 0.51 and seconds >= 0.5
    #assert result == [(0.1, TIMEOUT), (0.3, TIMEOUT), (0.5, TIMEOUT)]



if __name__ == '__main__':
    test_singleton()
    test_timeouts()
