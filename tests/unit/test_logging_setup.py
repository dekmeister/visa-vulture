"""Tests for the logging configuration module."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from visa_vulture.logging_config.setup import GUILogHandler, setup_logging


@pytest.fixture(autouse=True)
def reset_loggers():
    """Reset root logger and third-party loggers after each test."""
    yield
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    # Reset third-party logger levels
    for name in [
        "matplotlib",
        "matplotlib.font_manager",
        "matplotlib.backends",
        "pyvisa",
        "PIL",
    ]:
        logging.getLogger(name).setLevel(logging.NOTSET)


class TestThirdPartyLoggerSuppression:
    """Tests for third-party logger suppression in debug mode."""

    def test_debug_mode_suppresses_matplotlib(self, tmp_path: Path) -> None:
        """Matplotlib logger is set to WARNING when app is in DEBUG mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="DEBUG")
        assert logging.getLogger("matplotlib").level == logging.WARNING

    def test_debug_mode_suppresses_matplotlib_font_manager(
        self, tmp_path: Path
    ) -> None:
        """Matplotlib font_manager logger is suppressed in DEBUG mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="DEBUG")
        assert logging.getLogger("matplotlib.font_manager").level == logging.WARNING

    def test_debug_mode_suppresses_pyvisa(self, tmp_path: Path) -> None:
        """PyVISA logger is set to WARNING when app is in DEBUG mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="DEBUG")
        assert logging.getLogger("pyvisa").level == logging.WARNING

    def test_debug_mode_suppresses_pil(self, tmp_path: Path) -> None:
        """PIL logger is set to WARNING when app is in DEBUG mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="DEBUG")
        assert logging.getLogger("PIL").level == logging.WARNING

    def test_info_mode_does_not_suppress_third_party(self, tmp_path: Path) -> None:
        """Third-party loggers are not explicitly overridden in INFO mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="INFO")
        # NOTSET means the logger inherits from root (which is INFO)
        assert logging.getLogger("matplotlib").level == logging.NOTSET
        assert logging.getLogger("pyvisa").level == logging.NOTSET

    def test_app_loggers_remain_at_debug(self, tmp_path: Path) -> None:
        """Application loggers stay at DEBUG level in debug mode."""
        setup_logging(log_file=tmp_path / "test.log", log_level="DEBUG")
        app_logger = logging.getLogger("visa_vulture.model.equipment")
        assert app_logger.getEffectiveLevel() == logging.DEBUG


class TestGUILogHandler:
    """Tests for the custom GUI log handler."""

    def test_handler_emits_to_callback(self) -> None:
        """GUILogHandler calls the callback with log records."""
        records = []
        handler = GUILogHandler(callback=records.append)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        handler.emit(record)
        assert len(records) == 1
        assert records[0].msg == "test message"

    def test_handler_without_callback_does_not_error(self) -> None:
        """GUILogHandler with no callback does not raise on emit."""
        handler = GUILogHandler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        handler.emit(record)  # Should not raise

    def test_set_callback_updates_handler(self) -> None:
        """set_callback updates the callback used by emit."""
        records = []
        handler = GUILogHandler()
        handler.set_callback(records.append)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        handler.emit(record)
        assert len(records) == 1


class TestSetupLogging:
    """Tests for the setup_logging function."""

    def test_returns_gui_handler(self, tmp_path: Path) -> None:
        """setup_logging returns a GUILogHandler instance."""
        handler = setup_logging(log_file=tmp_path / "test.log")
        assert isinstance(handler, GUILogHandler)

    def test_uses_provided_gui_handler(self, tmp_path: Path) -> None:
        """setup_logging uses an existing GUILogHandler if provided."""
        existing = GUILogHandler()
        result = setup_logging(
            log_file=tmp_path / "test.log", gui_handler=existing
        )
        assert result is existing

    def test_root_logger_level_set(self, tmp_path: Path) -> None:
        """Root logger level is set to the configured level."""
        setup_logging(log_file=tmp_path / "test.log", log_level="WARNING")
        assert logging.getLogger().level == logging.WARNING
