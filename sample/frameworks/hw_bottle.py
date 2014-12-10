import bottle
import squall
import os.path
from bottle import jinja2_view, route
from squall.scgi2wsgi import wsgi
from squall.utilites import configLogger

template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')


@route('/hello')
@route('/hello/<name>')
@jinja2_view('hello.html', template_lookup=[template_path])
def hello(name='World'):
    return dict(name=name)

app = bottle.default_app()

if __name__ == '__main__':
    import logging
    configLogger(logging.INFO)
    squall.streamServer(wsgi(app), ("127.0.0.1", 7000), 64)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()
