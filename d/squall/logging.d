module squall.logging;

import std.string;
import std.c.stdio;

/* Level codes */
enum : int
{
    LOG_CRITICAL = 50,
    LOG_ERROR    = 40,
    LOG_WARNING  = 30,
    LOG_INFO     = 20,
    LOG_TRACE    = 10,
    LOG_NOTSET   = 0,
}

extern(C) {
    alias LoggerCallback = int function(int level, const(char*) message);
}


class Logger
{
    private void delegate(string message) critical;
    private void delegate(string message) error;
    private void delegate(string message) warning;
    private void delegate(string message) info;
    private void delegate(string message) trace;

    bool setup(int level, LoggerCallback logger_callback = null)
    {
        if (level > LOG_NOTSET) {
            if (level == LOG_CRITICAL)
                this.critical = (string message) { logger_callback(LOG_CRITICAL, toStringz(message)); };
            if (level >= LOG_ERROR)
                this.error = (string message) { logger_callback(LOG_ERROR, toStringz(message)); };
            if (level >= LOG_WARNING)
                this.warning = (string message) { logger_callback(LOG_WARNING, toStringz(message)); };
            if (level >= LOG_INFO)
                this.info = (string message) { logger_callback(LOG_INFO, toStringz(message)); };
            if (level >= LOG_TRACE)
                this.trace = (string message) { logger_callback(LOG_TRACE, toStringz(message)); };
            debug trace("extern(C) squall.logging activated.");
            return true;
        } else {
            this.critical = null;
            this.error = null;
            this.warning = null;
            this.info = null;
            this.trace = null;
            return false;
        }
    }
}


debug {
    /* Logs debug message. */
    void trace(A...)(string message, A args) {
        if ((default_logger !is null) && (default_logger.trace !is null))
            default_logger.trace(format(message, args));
    }
}

/* Logs info message. */
void info(A...)(string message, A args) {
    if ((default_logger !is null) && (default_logger.info !is null))
        default_logger.info(format(message, args));
}

/* Logs warning message. */
void warning(A...)(string message, A args) {
    if ((default_logger !is null) && (default_logger.warning !is null))
        default_logger.warning(format(message, args));
}

/* Logs error message. */
void error(A...)(string message, A args) {
    if ((default_logger !is null) && (default_logger.error !is null))
        default_logger.error(format(message, args));
}

/* Logs critical message. */
void critical(A...)(string message, A args) {
    if ((default_logger !is null) && (default_logger.critical !is null))
        default_logger.critical(format(message, args));
}


private Logger default_logger;

static this() {
    default_logger = new Logger();
}

static ~this() {
    destroy(default_logger);
    default_logger = null;
}

@property Logger logger() nothrow {
    return default_logger;
}