import std.string;
import core.runtime;
import squall.logging;
import squall.dispatcher;


private Dispatcher dispatcher;

static ~this() {
    logger.setup(LOG_NOTSET);
    destroy(dispatcher);
    dispatcher = null;
}


extern(C) {

    __gshared {
        int event_READ;
        int event_ERROR;
        int event_WRITE;
        int event_IDLE;
        int event_TIMEOUT;
        int event_CLEANUP;
    }

    int library_init() nothrow
    {
        try {
            if (dispatcher is null) {
                Runtime.initialize();
                dispatcher = new Dispatcher();
                event_READ = READ;
                event_WRITE = WRITE;
                event_ERROR = ERROR;
                event_IDLE = IDLE;
                event_TIMEOUT = TIMEOUT;
                event_CLEANUP = CLEANUP;
                return true;
            }
            return false;
        } catch (Exception) {
            return false;
        }
    }

    int logger_setup(int level, LoggerCallback logger_callback)
    {
        try {
            return logger.setup(level, logger_callback);
        } catch (Exception) {
            return false;
        }
    }

    int dispatcher_start(EventCallback event_callback) nothrow
    {
        try {
            return dispatcher.start(event_callback);
        } catch (Exception) {
            return false;
        }
    }

    int dispatcher_stop() nothrow
    {
        try {
            return dispatcher.stop();
        } catch (Exception) {
            return false;
        }
    }

    int dispatcher_call(void* context) nothrow
    {
        try {
            return dispatcher.call(context);
        } catch (Exception) {
            return false;
        }
    }

    int dispatcher_watch(void* context, int fd, int eventmask, double timeout) nothrow
    {
        try {
            return dispatcher.watch(context, fd, eventmask, timeout);
        } catch (Exception) {
            return false;
        }
    }
}