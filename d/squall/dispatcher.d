module squall.dispatcher;

import std.algorithm;
import squall.logging;
import squall.event.abc;

version(LIBEV4) {
    import squall.event.libev4 : Loop;
    public import squall.event.libev4 : IdleWatcher, TimeoutWatcher, TimedIOWatcher, WatcherCallback;
    public import squall.event.libev4 : NONE, IDLE, READ, WRITE, TIMEOUT, CLEANUP, ERROR;
    version(Posix) {
        public import squall.event.libev4 : SignalWatcher, SIGNAL;
        public import core.stdc.signal : SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM;
    }
}


extern(C) {
    alias EventCallback = int function(void* context, int revents);
}


/* Event dispatcher */
class Dispatcher : Loop
{
private:
    version(Posix) ISignalWatcher sigint_watcher;
    EventCallback event_callback;
    void*[] call_contexts;
    IWatcher idle_watcher;
    IWatcher[] watchers;

public:
    /* Default constructor */
    this() {
        super();
        idle_watcher = new IdleWatcher(this,
            (watcher, revents) {
                auto copy_call_contexts = call_contexts.dup;
                call_contexts.length = 0;
                foreach (context; copy_call_contexts) {
                    event_callback(context, revents);
                }
                watcher.stop();
            });

        version(Posix) {
            sigint_watcher = new SignalWatcher(this, SIGINT,
                (_, revents) {
                    if (revents & SIGNAL)
                        stop();
                });
        }
    }

    /* Starts event dispatcher. */
    bool start(EventCallback event_callback)
    {
        info("Event dispatcher is starting.");
        this.event_callback = event_callback;
        version(Posix) sigint_watcher.start();
        return super.start();
    }

    /* Stops event dispatcher. */
    override bool stop()
    {
        if (super.stop()) {
            idle_watcher.stop();
            version(Posix) sigint_watcher.stop();
            foreach (watcher; watchers)
                watcher.stop();
            info("Event dispatcher has stopped.");
            return true;
        }
        return false;
    }

    /* Setup idle task */
    bool call(void* context)
    {
        call_contexts ~= context;
        if (!idle_watcher.started)
            idle_watcher.start();
        return true;
    }

    /* Setup event task */
    bool watch(void* context, int fd, int eventmask, double timeout)
    {
        IWatcher watcher = new TimedIOWatcher(this, fd, eventmask, timeout,
            (watcher, revents) {
                auto pos = countUntil(watchers, watcher);
                if (pos>=0)
                    watchers = watchers[0..pos] ~ watchers[pos+1..$];
                watcher.stop();
                event_callback(context, revents);
            });
        watchers ~= watcher;
        return watcher.start();
    }
}