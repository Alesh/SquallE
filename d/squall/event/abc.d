module squall.event.abc;

/* Event loop interface */
interface ILoop
{
    /* Returns true if event loop is closed */
    @property bool closed();
    /* Returns true if event loop is started. */
    @property bool started();
    /* Returns internal loop time as timestamp. */
    @property double time();
    /* Starts event loop. */
    bool start();
    /* Stops event loop. */
    bool stop();
    /* Closes event loop */
    bool close();
}

/* Event watcher interface */
interface IWatcher
{
    /* Starts event watching. */
    bool start();
    /* Stops event watching. */
    bool stop();
    /* Closes event watching. */
    bool close();
    /* Returns true if watcher is closed. */
    @property bool closed();
    /* Returns true if watcher is active. */
    @property bool started();
    /* Sets watcher callback. */
    @property void callback(void delegate(IWatcher watcher, int revents) callback);
}


/* "Timeout" event watcher interface */
interface ITimeoutWatcher : IWatcher {
    /* Returns current timeout. */
    @property double timeout();
    /* Returns current timeout. */
    @property void timeout(double value);
}


/* "I/O"  event watcher interface */
interface ITimedIOWatcher : ITimeoutWatcher
{
    /* Returns watching file descriptor. */
    @property int fileno();
    /* Sets watching file descriptor. */
    @property void fileno(int value);
    /* Returns watching I/O event mask. */
    @property int event_mask();
    /* Sets watching I/O event mask. */
    @property void event_mask(int value);
}

version(Posix) {
    /* "Signal" event watcher interface */
    interface ISignalWatcher : IWatcher
    {
        /* Returns watched signal. */
        @property int signum();
    }
}