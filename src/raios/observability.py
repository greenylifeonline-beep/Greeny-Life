"""Logging aligned with GreenyLifeBrain (console + logs/ file).

Reuses the existing ``logs/`` directory and formatter pattern from
``brain.py`` ``GreenyLifeBrain._setup_logging``. Does not create a second
observability stack.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


_LOGGER_NAME = "RAIOS.NeuroLingua"


def get_logger(
    name: str = _LOGGER_NAME,
    *,
    repo_path: Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_dir = (repo_path or Path.cwd()) / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"neuro-lingua-{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Local-first: logging must never block interpretation.
        logger.warning("Could not attach file handler under %s", log_dir)

    logger.propagate = False
    return logger
