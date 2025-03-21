import logging


def set_global_logging_level(level: int) -> None:
    """Set the global logging level."""
    logging.getLogger().setLevel(level)
