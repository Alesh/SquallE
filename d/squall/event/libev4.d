module squall.event.libev4;

import deimos.ev;
import squall.logging;
import squall.event.abc;


/* Event codes */
enum : int
{
    NONE    = EV_NONE,
    READ    = EV_READ,
    IDLE    = EV_IDLE,
    WRITE   = EV_WRITE,
    TIMEOUT = EV_TIMER,
    SIGNAL  = EV_SIGNAL,
    CLEANUP = EV_CLEANUP,
    ERROR   = EV_ERROR,
}


/* Event loop */
class Loop : ILoop
{
private:
    private ev_loop_t* p_loop;
    private bool m_closed, m_started;

public:
    /* Returns true if event loop is closed */
    @property bool closed() { return p_loop is null; }

    /* Returns true if event loop is started. */
    @property bool started() { return m_started; }

    /* Returns internal loop time as timestamp. */
    @property double time() { return ev_time(); }


    /* Default constructor. */
    this() {
        p_loop = ev_loop_new(EVFLAG_AUTO);
    }

    /* Destructor. */
    ~this() {
        close();
    }

    /* Starts event loop. */
    bool start() {
        if ((!closed)&&(!started)) {
            m_started = true;
            ev_run(p_loop, 0);
            return true;
        }
        return false;
    }

    /* Stops event loop. */
    bool stop() {
        if ((!closed)&&(started)) {
            ev_break(p_loop, EVBREAK_ALL);
            m_started = false;
            return true;
        }
        return false;
    }

    /* Closes event loop */
    bool close() {
        if (!closed) {
            if (started)
                stop();
            ev_loop_destroy(p_loop);
            p_loop = null;
            return true;
        }
        return false;
    }
}


alias WatcherCallback = void delegate(IWatcher watcher, int revents);

/* LIBEV4 callback */
extern(C) private static void ev_callback(T)(ev_loop_t* p_loop, T* p_watcher, int revents)
{
    auto watcher = cast(Watcher)p_watcher.data;
    if (revents & EV_CLEANUP)
        watcher.close();
    watcher.m_callback(watcher, revents);
}

/* Abstract base class of watchers. */
abstract class Watcher : IWatcher
{
private:
    ev_loop_t* p_loop;
    ev_cleanup cleanup_watcher;
    WatcherCallback m_callback;

    /* Private constructor */
    this(ILoop loop, WatcherCallback callback)
    {
        this.callback = callback;
        p_loop = (cast(Loop)loop).p_loop;
        ev_cleanup_init(&cleanup_watcher, &ev_callback!ev_cleanup);
        cleanup_watcher.data = cast(void*)(this);
    }

public:
    /* Returns true if watcher is closed. */
    @property bool closed() { return p_loop is null; }
    /* Returns true if watcher is active. */
    @property bool started() { return ev_is_active(&cleanup_watcher); }
    /* Sets watcher callback. */
    @property void callback(WatcherCallback callback) {
        m_callback = callback;
    }

    /* Destructor. */
    ~this() {
        close();
    }

    /* Starts event watching. */
    bool start()
    {
        if ((!closed)&&(!started)) {
            ev_cleanup_start(p_loop, &cleanup_watcher);
            return true;
        }
        return false;
    }

    /* Stops event watching. */
    bool stop()
    {
        if ((!closed)&&(started)) {
            ev_cleanup_stop(p_loop, &cleanup_watcher);
            return true;
        }
        return false;
    }

    /* Closes event watching. */
    bool close()
    {
        if (!closed) {
            if (started)
                stop();
            p_loop = null;
            return true;
        }
        return false;
    }
}


/* "Idle" event watcher */
class IdleWatcher : Watcher
{
private:
    ev_idle idle_watcher;

public:

    /* Default constructor */
    this(ILoop loop, WatcherCallback callback)
    {
        super(loop, callback);
        ev_idle_init(&idle_watcher, &ev_callback!ev_idle);
        idle_watcher.data = cast(void*)this;
    }

    /* Starts event watching. */
    override bool start()
    {
        if (super.start()) {
            ev_idle_start(p_loop, &idle_watcher);
            return true;
        }
        return false;
    }

    /* Stops event watching. */
    override bool stop()
    {
        if (super.stop()) {
            if (ev_is_active(&idle_watcher))
                ev_idle_stop(p_loop, &idle_watcher);
            return true;
        }
        return false;
    }
}


/* "Timeout" event watcher */
class TimeoutWatcher : Watcher, ITimeoutWatcher
{
private:
    ev_timer timer_watcher;

public:
    /* Returns current timeout. */
    @property double timeout() { return timer_watcher.repeat; };

    /* Default constructor */
    this(ILoop loop, double timeout, WatcherCallback callback)
    {
        super(loop, callback);
        ev_timer_init(&timer_watcher, &ev_callback!ev_timer, timeout, timeout);
        timer_watcher.data = cast(void*)this;
    }

    /* Starts event watching. */
    override bool start()
    {
        if (super.start()) {
            if (timeout > 0)
                ev_timer_start(p_loop, &timer_watcher);
            return true;
        }
        return false;
    }

    /* Stops event watching. */
    override bool stop()
    {
        if (super.stop()) {
            if (ev_is_active(&timer_watcher))
                ev_timer_stop(p_loop, &timer_watcher);
            return true;
        }
        return false;
    }

    /* Sets current timeout. */
    @property void timeout(double value) {
        if (ev_is_active(&timer_watcher))
            ev_timer_stop(p_loop, &timer_watcher);
        ev_timer_init(&timer_watcher, &ev_callback!ev_timer, value, value);
        if (started && (timeout > 0))
            ev_timer_start(p_loop, &timer_watcher);
    }
}


/* "I/O" event watcher */
class TimedIOWatcher : TimeoutWatcher, ITimedIOWatcher
{
private:
    ev_io io_watcher;

public:
    /* Returns watching file descriptor. */
    @property int fileno() { return io_watcher.fd; }
    /* Returns watching I/O event mask. */
    @property int event_mask() { return io_watcher.events & (READ|WRITE); }

    /* Default constructor */
    this(ILoop loop, int fileno, int event_mask, double timeout, WatcherCallback callback)
    {
        super(loop, timeout, callback);
        ev_io_init(&io_watcher, &ev_callback!ev_io, fileno, event_mask);
        io_watcher.data = cast(void*)this;
    }

    /* Starts event watching. */
    override bool start()
    {
        if (super.start()) {
            if ((fileno >= 0)&&(event_mask > 0))
                ev_io_start(p_loop, &io_watcher);
            return true;
        }
        return false;
    }

    /* Stops event watching. */
    override bool stop()
    {
        if (super.stop()) {
            if (ev_is_active(&io_watcher))
                ev_io_stop(p_loop, &io_watcher);
            return true;
        }
        return false;
    }

    /* Sets watching  file descriptor. */
    @property void fileno(int value) {
        if (value != io_watcher.fd) {
            if (ev_is_active(&io_watcher))
                ev_io_stop(p_loop, &io_watcher);
            ev_io_init(&io_watcher, &ev_callback!ev_io, value, event_mask);
            if (started && (fileno >= 0) && (event_mask > 0))
                ev_io_start(p_loop, &io_watcher);
        }
    }

    /* Sets watching I/O event mask. */
    @property void event_mask(int value) {
        if (value != io_watcher.events) {
            if (ev_is_active(&io_watcher))
                ev_io_stop(p_loop, &io_watcher);
            ev_io_init(&io_watcher, &ev_callback!ev_io, fileno, value);
            if (started && (fileno >= 0) && (event_mask > 0))
                ev_io_start(p_loop, &io_watcher);
        }
    }
}


version(Posix) {

    /* "Signal" event watcher */
    class SignalWatcher : Watcher, ISignalWatcher
    {
    private:
        ev_signal signal_watcher;

    public:
        /* Returns watched signal. */
        @property int signum() { return signal_watcher.signum; }

        /* Default constructor */
        this(ILoop loop, int signum, WatcherCallback callback)
        {
            super(loop, callback);
            ev_signal_init(&signal_watcher, &ev_callback!ev_signal, signum);
            signal_watcher.data = cast(void*)this;
        }

        /* Starts event watching. */
        override bool start()
        {
            if (super.start()) {
                ev_signal_start(p_loop, &signal_watcher);
                return  true;
            }
            return false;
        }

        /* Stops event watching. */
        override bool stop()
        {
            if (super.stop()) {
                if (ev_is_active(&signal_watcher))
                    ev_signal_stop(p_loop, &signal_watcher);
                return true;
            }
            return false;
        }
    }
}