import logging
from logging.handlers import RotatingFileHandler

from . import state
from .paths import LOG_DIR, LOG_PATH


LOGGER_NAME = "openanima"
MAX_RECENT_DIAGNOSTICS = 100
_CONFIGURED = False
_SETUP_WARNING_PRINTED = False


def logger():
    return logging.getLogger(LOGGER_NAME)


def configure_logging():
    global _CONFIGURED, _SETUP_WARNING_PRINTED
    app_logger = logger()
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False

    if _CONFIGURED:
        return app_logger

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_PATH,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
        _CONFIGURED = True
    except Exception as exc:
        warning = f"Logging setup failed: {exc}"
        if not _SETUP_WARNING_PRINTED:
            print(f"OpenAnima warning: {warning}")
            _SETUP_WARNING_PRINTED = True

    return app_logger


def _record_recent(level, message):
    state.RECENT_DIAGNOSTICS.append({"level": level, "message": str(message)})
    del state.RECENT_DIAGNOSTICS[:-MAX_RECENT_DIAGNOSTICS]


def log_info(message, *args, **kwargs):
    text = message % args if args else str(message)
    configure_logging().info(message, *args, **kwargs)
    _record_recent("INFO", text)


def log_warning(message, *args, **kwargs):
    text = message % args if args else str(message)
    state.CONFIG_WARNINGS.append(text)
    del state.CONFIG_WARNINGS[:-MAX_RECENT_DIAGNOSTICS]
    configure_logging().warning(message, *args, **kwargs)
    _record_recent("WARNING", text)


def log_error(message, *args, **kwargs):
    text = message % args if args else str(message)
    configure_logging().error(message, *args, **kwargs)
    _record_recent("ERROR", text)


def log_exception(message, *args, **kwargs):
    text = message % args if args else str(message)
    configure_logging().exception(message, *args, **kwargs)
    _record_recent("ERROR", text)


def recent_warnings_and_errors():
    return [item for item in state.RECENT_DIAGNOSTICS if item["level"] in {"WARNING", "ERROR"}]
