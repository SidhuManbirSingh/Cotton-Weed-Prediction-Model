"""Centralized rotating-file and console logging for CottonVision."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
_LOG_FILE = _LOGS_DIR / "cottonvision.log"
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_CONFIGURED = False


def _configure_root() -> None:
    """Attach console and rotating file handlers once for cottonvision loggers."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    root_logger = logging.getLogger("cottonvision")
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    if not root_logger.handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

        file_handler = RotatingFileHandler(
            _LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured child logger under the 'cottonvision' namespace."""
    _configure_root()
    short_name = name.removeprefix("cottonvision.")
    return logging.getLogger(f"cottonvision.{short_name}")


def get_log_file_path() -> Path:
    """Return the active rotating log file path."""
    _configure_root()
    return _LOG_FILE
