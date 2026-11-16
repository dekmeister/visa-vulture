"""Tests for main module helper functions."""

import sys
from unittest.mock import patch

import pytest

import visa_vulture.main as main_module
from visa_vulture.main import validate_visa_backend


class TestValidateVisaBackend:
    """Tests for validate_visa_backend function."""

    def test_invalid_backend_returns_error(self) -> None:
        """Invalid backend name returns error message."""
        result = validate_visa_backend("nonexistent_backend")
        assert result is not None
        assert "nonexistent_backend" in result
        assert "Available backends" in result

    def test_valid_sim_backend_returns_none(self) -> None:
        """'sim' backend is valid (pyvisa-sim is installed)."""
        result = validate_visa_backend("sim")
        assert result is None

    def test_valid_ivi_backend_returns_none(self) -> None:
        """'ivi' backend is always valid (built-in)."""
        result = validate_visa_backend("ivi")
        assert result is None


class TestReportStartupErrors:
    """Tests for report_startup_errors."""

    def test_prints_to_stderr_without_dialog_from_source(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        with patch.object(main_module.tk, "Tk") as mock_tk:
            main_module.report_startup_errors("Configuration errors", ["bad", "worse"])

        assert capsys.readouterr().err == (
            "Configuration errors:\n  - bad\n  - worse\n"
        )
        mock_tk.assert_not_called()

    def test_heading_only_when_no_errors(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        main_module.report_startup_errors("Failed to load configuration", [])
        assert capsys.readouterr().err == "Failed to load configuration\n"

    def test_shows_dialog_when_frozen(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        with (
            patch.object(main_module.tk, "Tk") as mock_tk,
            patch.object(main_module.messagebox, "showerror") as mock_showerror,
        ):
            main_module.report_startup_errors("Configuration errors", ["bad"])

        mock_showerror.assert_called_once()
        assert "  - bad" in mock_showerror.call_args.args[1]
        mock_tk.return_value.destroy.assert_called_once()
        # stderr is still written when available
        assert "  - bad" in capsys.readouterr().err

    def test_shows_dialog_when_stderr_is_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr(sys, "frozen", raising=False)
        monkeypatch.setattr(sys, "stderr", None)
        with (
            patch.object(main_module.tk, "Tk"),
            patch.object(main_module.messagebox, "showerror") as mock_showerror,
        ):
            main_module.report_startup_errors("Configuration errors", ["bad"])

        mock_showerror.assert_called_once()

    def test_no_display_does_not_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        with (
            patch.object(
                main_module.tk, "Tk", side_effect=main_module.tk.TclError("no display")
            ),
            patch.object(main_module.messagebox, "showerror") as mock_showerror,
        ):
            main_module.report_startup_errors("Configuration errors", ["bad"])

        mock_showerror.assert_not_called()
