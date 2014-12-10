"""`squall.adapters`"""
import functools

try:
    import bottle

    class bottle_app_adapter(object):
        """Bottle application adapter."""
        def __init__(self, default_app):
            self._default_app = default_app

        def __call__(self, environ, start_response):
            app = bottle.app.push()
            app.merge(self._default_app)
            try:
                out = app._handle(environ)
                app._handle = lambda environ: out
                if hasattr(out, '__next__') and hasattr(out, '__name__') and out.__name__ == 'async_view_wrapper':
                    out = yield from out
                result = app(environ, start_response)
            except bottle.HTTPResponse as out:
                result = app(environ, start_response)
            bottle.app.pop()
            return result

    def bottle_async_view(tpl_name, **defaults):
        """Bottle async view."""
        def decorator(func):
            @functools.wraps(func)
            def async_view_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                if hasattr(result, '__next__'):
                    next(result)
                    try:
                        while True:
                            event = yield
                            result.send(event)
                    except StopIteration as exc:
                        result = exc.value
                if isinstance(result, (dict, bottle.DictMixin)):
                    tplvars = defaults.copy()
                    tplvars.update(result)
                    return bottle.template(tpl_name, **tplvars)
                elif result is None:
                    return bottle.template(tpl_name, defaults)
                return result
            return async_view_wrapper
        return decorator

    bottle_async_jinja2_view = functools.partial(bottle_async_view, template_adapter=bottle.Jinja2Template)
    bottle_async_cheetah_view = functools.partial(bottle_async_view, template_adapter=bottle.CheetahTemplate)
    bottle_async_jinja2_view = functools.partial(bottle_async_view, template_adapter=bottle.Jinja2Template)


except:
    pass
