import logging

_INITIALIZED = False


def _init_once() -> None:
    """Initialize logging."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    logging.basicConfig(level=logging.INFO)
    _INITIALIZED = True


def set_global_logging_level(level: int | str) -> None:
    """Set the global logging level."""
    _init_once()
    logging.getLogger().setLevel(level)


def create_logger(name: str, level: int | str | None) -> logging.Logger:
    """Get a logger."""
    _init_once()
    out = logging.getLogger(name)
    if level is not None:
        out.setLevel(level)
    return out
