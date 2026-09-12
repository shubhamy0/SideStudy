"""Logging setup for Study Companion."""

import logging
import sys


# ANSI color codes for terminal output
class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color to console output."""

    LEVEL_COLORS = {
        logging.DEBUG: _Colors.DIM,
        logging.INFO: _Colors.CYAN,
        logging.WARNING: _Colors.YELLOW,
        logging.ERROR: _Colors.RED,
        logging.CRITICAL: _Colors.RED + _Colors.BOLD,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, _Colors.RESET)
        record.color = color
        record.reset = _Colors.RESET
        record.bold = _Colors.BOLD
        record.dim = _Colors.DIM
        return super().format(record)


def setup_logger(
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """Configure and return the application logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to a log file.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("study_companion")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates on re-init
    logger.handlers.clear()

    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        ColoredFormatter(
            fmt="{color}[{levelname:>7}]{reset} {dim}{name}{reset} — {message}",
            style="{",
        )
    )
    logger.addHandler(console_handler)

    # Optional file handler (no color)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="[{asctime}] [{levelname:>7}] {name} — {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "study_companion") -> logging.Logger:
    """Get a child logger by name.

    Args:
        name: Logger name (will be prefixed with 'study_companion.').

    Returns:
        Logger instance.
    """
    if name == "study_companion":
        return logging.getLogger(name)
    return logging.getLogger(f"study_companion.{name}")
