import bottle
import squall
import os.path
from bottle import route
from squall import coroutine
from squall.scgi2wsgi import wsgi
from squall.utilites import configLogger
from squall.adapters import bottle_app_adapter as adapter
from squall.adapters import bottle_async_jinja2_view as async_jinja2_view

template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')


@route('/hello')
@route('/hello/<name>')
@async_jinja2_view('hello.html', template_lookup=[template_path])
def hello(name='World'):
    yield from coroutine.sleep(1.0)
    yield from coroutine.sleep(1.0)
    yield from coroutine.sleep(1.0)
    yield from coroutine.sleep(1.0)
    return dict(name=name)


if __name__ == '__main__':
    import logging
    configLogger(logging.DEBUG)
    squall.streamServer(wsgi(adapter(bottle.default_app())), ("127.0.0.1", 7000), 64)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()
