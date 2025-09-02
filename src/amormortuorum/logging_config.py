import logging
import os


def configure_logging(default_level: int = logging.INFO) -> None:
    """Configure root logger with a sane default format.

    Respects AM_LOG_LEVEL env var if present.
    """
    level_name = os.getenv("AM_LOG_LEVEL")
    level = default_level
    if level_name:
        level = getattr(logging, level_name.upper(), default_level)
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    )
