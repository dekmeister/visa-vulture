"""Tests for frozen/non-frozen path resolution."""

import sys
from pathlib import Path

import pytest

from visa_vulture.utils import app_paths


@pytest.fixture
def frozen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Simulate running as a packaged executable located in tmp_path/app."""
    exe = tmp_path / "app" / "visa-vulture.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    return exe


@pytest.fixture
def not_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)


class TestIsFrozen:
    def test_false_from_source(self, not_frozen: None) -> None:
        assert app_paths.is_frozen() is False

    def test_true_when_frozen(self, frozen: Path) -> None:
        assert app_paths.is_frozen() is True


class TestCustomInstrumentsDir:
    def test_uses_cwd_from_source(
        self, not_frozen: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert app_paths.resolve_custom_instruments_dir() == tmp_path / "instruments"

    def test_uses_exe_dir_when_frozen(
        self, frozen: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Working directory must not matter when frozen
        monkeypatch.chdir(tmp_path)
        expected = frozen.resolve().parent / "instruments"
        assert app_paths.resolve_custom_instruments_dir() == expected


class TestResolveLogFile:
    def test_relative_unchanged_from_source(self, not_frozen: None) -> None:
        assert app_paths.resolve_log_file("app.log") == Path("app.log")

    def test_relative_goes_to_user_data_dir_when_frozen(self, frozen: Path) -> None:
        result = app_paths.resolve_log_file("logs/app.log")
        assert result == app_paths.user_data_dir() / "logs" / "app.log"

    def test_absolute_unchanged_when_frozen(self, frozen: Path, tmp_path: Path) -> None:
        absolute = tmp_path / "custom.log"
        assert app_paths.resolve_log_file(absolute) == absolute


class TestUserDataDir:
    def test_windows_uses_localappdata(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
        assert app_paths.user_data_dir() == tmp_path / app_paths.APP_DIR_NAME

    def test_macos_uses_application_support(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "platform", "darwin")
        expected = (
            Path.home() / "Library" / "Application Support" / app_paths.APP_DIR_NAME
        )
        assert app_paths.user_data_dir() == expected

    def test_linux_honours_xdg_state_home(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        assert app_paths.user_data_dir() == tmp_path / app_paths.APP_DIR_NAME

    def test_linux_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "linux")
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        expected = Path.home() / ".local" / "state" / app_paths.APP_DIR_NAME
        assert app_paths.user_data_dir() == expected
