import squall
from flask import Flask
from flask import render_template
from squall.scgi2wsgi import wsgi
from squall.utilites import configLogger

app = Flask(__name__)


@app.route('/hello/')
@app.route('/hello/<name>')
def hello(name=None):
    return render_template('hello.html', name=name)


if __name__ == '__main__':
    import logging
    configLogger(logging.INFO)
    squall.streamServer(wsgi(app), ("127.0.0.1", 7000), 64)
    try:
        squall.start()
    except KeyboardInterrupt:
        squall.stop()
