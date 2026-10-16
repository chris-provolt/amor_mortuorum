import logging
import sys
from pathlib import Path
from typing import Optional


def configure_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> None:
    """Log to stdout, or to ``log_file`` when given or when there is no console.

    A PyInstaller ``--windowed`` build has ``sys.stdout`` set to ``None``; without
    a file handler every log call would raise and the first error would be lost.
    """
    handler: logging.Handler
    if log_file is None and sys.stdout is None:
        log_file = Path.cwd() / "amor.log"
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    else:
        handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates in repeated test runs
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
