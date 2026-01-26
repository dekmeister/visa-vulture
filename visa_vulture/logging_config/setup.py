"""Logging configuration and custom handlers."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable


class GUILogHandler(logging.Handler):
    """
    Custom logging handler that emits log records to a GUI callback.

    The callback is called from the logging thread, so it must be thread-safe
    or schedule updates to the main thread.
    """

    def __init__(self, callback: Callable[[logging.LogRecord], None] | None = None):
        """
        Initialize the handler.

        Args:
            callback: Function to call with each log record. Can be set later.
        """
        super().__init__()
        self._callback = callback

    def set_callback(self, callback: Callable[[logging.LogRecord], None]) -> None:
        """Set the callback function for log records."""
        self._callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the callback if set."""
        if self._callback is not None:
            try:
                self._callback(record)
            except Exception:
                self.handleError(record)


def setup_logging(
    log_file: str | Path = "equipment_controller.log",
    log_level: str = "INFO",
    gui_handler: GUILogHandler | None = None,
) -> GUILogHandler:
    """
    Configure application logging.

    Sets up:
    - Root logger with specified level
    - Rotating file handler (10MB max, 5 backups)
    - Console handler for development
    - Optional GUI handler for displaying logs in the application

    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        gui_handler: Optional existing GUILogHandler to use

    Returns:
        The GUILogHandler instance (created or passed in)
    """
    # Get numeric level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # GUI handler
    if gui_handler is None:
        gui_handler = GUILogHandler()
    gui_handler.setLevel(numeric_level)
    gui_handler.setFormatter(formatter)
    root_logger.addHandler(gui_handler)

    # Suppress noisy third-party loggers in debug mode.
    # These libraries emit excessive debug output that is not relevant
    # to application debugging and can overwhelm the GUI log panel.
    _NOISY_LOGGERS = [
        "matplotlib",
        "matplotlib.font_manager",
        "matplotlib.backends",
        "matplotlib.pyplot",
        "matplotlib.colorbar",
        "matplotlib.ticker",
        "pyvisa",
        "PIL",
        "PIL.PngImagePlugin",
    ]

    if numeric_level <= logging.DEBUG:
        for logger_name in _NOISY_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    logging.info("Logging configured: level=%s, file=%s", log_level, log_path)

    return gui_handler
