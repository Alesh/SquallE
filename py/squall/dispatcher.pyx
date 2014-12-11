"""`squall.dispatcher`"""
from squall.utilites import log

READ = None
WRITE = None
ERROR = None
IDLE = None
TIMEOUT = None

cdef extern:
    int event_READ
    int event_WRITE
    int event_ERROR
    int event_IDLE
    int event_TIMEOUT
    int event_CLEANUP

    int library_init()

    ctypedef void(*LoggerCallback)(int level, const char* message)
    int logger_setup(int level, LoggerCallback logger_callback)

    ctypedef void(*EventCallback)(void* context, int revents)
    int dispatcher_start(EventCallback event_callback)
    int dispatcher_stop()

    int dispatcher_call(void* context)
    int dispatcher_watch(void* context, int fd, int eventmask, double timeout)


library_initialized = False
# init external squall library
if not library_initialized:
    if library_init():
        READ = event_READ
        WRITE = event_WRITE
        ERROR = event_ERROR
        IDLE = event_IDLE
        TIMEOUT = event_TIMEOUT
        CLEANUP = event_CLEANUP
    else:
        raise ImportError("Cannot initialize external squall library.")



cdef void c_logger_callback(int level, const char* message):
    try:
        log.log(level, message.decode('utf8'))
    except:
        pass

def setup_logging(level):
    """Setups logging system."""
    return logger_setup(level, c_logger_callback)


event_callbacks = dict()
cdef void c_event_callback(void* context, int revents):
    try:
        handle = <object>context
        event_callback = event_callbacks.pop(handle)
        event_callback(handle, revents)
    except:
        pass

def start():
    """Starts event dispatching."""
    return dispatcher_start(c_event_callback)

def stop():
    """Stops event dispatching."""
    return dispatcher_stop()

def call(handle, callback):
    """Setups the next idle callback."""
    event_callbacks[handle] = callback
    context = <void*>handle
    return dispatcher_call(context)

def watch(handle, callback, fd=-1, eventmask=0, timeout=0):
    """Setups the event callback."""
    event_callbacks[handle] = callback
    return dispatcher_watch(<void*>handle, fd, eventmask, timeout)
