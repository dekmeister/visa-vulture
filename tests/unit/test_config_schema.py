"""Tests for the config schema module."""

import json
from pathlib import Path

import pytest

from visa_vulture.config.schema import AppConfig, validate_config


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        """AppConfig has correct default values."""
        config = AppConfig()
        assert config.simulation_mode is False
        assert config.simulation_file == "simulation/instruments.yaml"
        assert config.log_file == "equipment_controller.log"
        assert config.log_level == "INFO"
        assert config.window_title == "VISA Vulture"
        assert config.window_width == 1200
        assert config.window_height == 800
        assert config.poll_interval_ms == 100

    def test_custom_values(self) -> None:
        """AppConfig can be created with custom values."""
        config = AppConfig(
            simulation_mode=True,
            log_level="DEBUG",
            window_width=800,
        )
        assert config.simulation_mode is True
        assert config.log_level == "DEBUG"
        assert config.window_width == 800


class TestValidateConfigHappyPath:
    """Tests for validate_config happy path."""

    def test_valid_config_returns_app_config(self, config_fixtures_path: Path) -> None:
        """Valid config returns AppConfig with no errors."""
        with open(config_fixtures_path / "valid_config.json") as f:
            config_dict = json.load(f)

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.simulation_mode is True
        assert config.log_level == "DEBUG"

    def test_valid_minimal_config_uses_defaults(
        self, config_fixtures_path: Path
    ) -> None:
        """Empty config uses all defaults."""
        with open(config_fixtures_path / "valid_config_minimal.json") as f:
            config_dict = json.load(f)

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.simulation_mode is False
        assert config.log_level == "INFO"
        assert config.window_width == 1200


class TestValidateConfigSimulationMode:
    """Tests for simulation_mode validation."""

    def test_invalid_simulation_mode_type_returns_error(self) -> None:
        """Non-boolean simulation_mode returns error."""
        config, errors = validate_config({"simulation_mode": "yes"})
        assert config is None
        assert any("simulation_mode must be boolean" in e for e in errors)

    def test_simulation_mode_true(self) -> None:
        """Boolean True is accepted."""
        config, errors = validate_config({"simulation_mode": True})
        assert errors == []
        assert config is not None
        assert config.simulation_mode is True


class TestValidateConfigSimulationFile:
    """Tests for simulation_file validation."""

    def test_invalid_simulation_file_type_returns_error(self) -> None:
        """Non-string simulation_file returns error."""
        config, errors = validate_config({"simulation_file": 123})
        assert config is None
        assert any("simulation_file must be string" in e for e in errors)


class TestValidateConfigLogFile:
    """Tests for log_file validation."""

    def test_invalid_log_file_type_returns_error(self) -> None:
        """Non-string log_file returns error."""
        config, errors = validate_config({"log_file": 123})
        assert config is None
        assert any("log_file must be string" in e for e in errors)


class TestValidateConfigLogLevel:
    """Tests for log_level validation."""

    def test_invalid_log_level_type_returns_error(self) -> None:
        """Non-string log_level returns error."""
        config, errors = validate_config({"log_level": 123})
        assert config is None
        assert any("log_level must be string" in e for e in errors)

    def test_invalid_log_level_value_returns_error(
        self, config_fixtures_path: Path
    ) -> None:
        """Invalid log level value returns error."""
        with open(config_fixtures_path / "invalid_config_invalid_log_level.json") as f:
            config_dict = json.load(f)

        config, errors = validate_config(config_dict)
        assert config is None
        assert any("log_level must be one of" in e for e in errors)

    def test_log_level_case_insensitive(self) -> None:
        """Log level is case insensitive."""
        config, errors = validate_config({"log_level": "debug"})
        assert errors == []
        assert config is not None
        assert config.log_level == "DEBUG"

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_all_valid_log_levels(self, level: str) -> None:
        """All valid log levels are accepted."""
        config, errors = validate_config({"log_level": level})
        assert errors == []
        assert config is not None
        assert config.log_level == level


class TestValidateConfigWindowSettings:
    """Tests for window settings validation."""

    def test_invalid_window_title_type_returns_error(self) -> None:
        """Non-string window_title returns error."""
        config, errors = validate_config({"window_title": 123})
        assert config is None
        assert any("window_title must be string" in e for e in errors)

    def test_window_width_below_minimum_returns_error(self) -> None:
        """window_width below 400 returns error."""
        config, errors = validate_config({"window_width": 300})
        assert config is None
        assert any("window_width must be integer >= 400" in e for e in errors)

    def test_window_width_non_integer_returns_error(self) -> None:
        """Non-integer window_width returns error."""
        config, errors = validate_config({"window_width": "wide"})
        assert config is None
        assert any("window_width must be integer >= 400" in e for e in errors)

    def test_window_height_below_minimum_returns_error(self) -> None:
        """window_height below 300 returns error."""
        config, errors = validate_config({"window_height": 200})
        assert config is None
        assert any("window_height must be integer >= 300" in e for e in errors)

    def test_window_height_non_integer_returns_error(self) -> None:
        """Non-integer window_height returns error."""
        config, errors = validate_config({"window_height": "tall"})
        assert config is None
        assert any("window_height must be integer >= 300" in e for e in errors)

    def test_window_width_at_minimum(self) -> None:
        """window_width of exactly 400 is valid."""
        config, errors = validate_config({"window_width": 400})
        assert errors == []
        assert config is not None
        assert config.window_width == 400

    def test_window_height_at_minimum(self) -> None:
        """window_height of exactly 300 is valid."""
        config, errors = validate_config({"window_height": 300})
        assert errors == []
        assert config is not None
        assert config.window_height == 300


class TestValidateConfigPollInterval:
    """Tests for poll_interval_ms validation."""

    def test_poll_interval_below_minimum_returns_error(self) -> None:
        """poll_interval_ms below 10 returns error."""
        config, errors = validate_config({"poll_interval_ms": 5})
        assert config is None
        assert any("poll_interval_ms must be integer >= 10" in e for e in errors)

    def test_poll_interval_non_integer_returns_error(self) -> None:
        """Non-integer poll_interval_ms returns error."""
        config, errors = validate_config({"poll_interval_ms": "fast"})
        assert config is None
        assert any("poll_interval_ms must be integer >= 10" in e for e in errors)

    def test_poll_interval_at_minimum(self) -> None:
        """poll_interval_ms of exactly 10 is valid."""
        config, errors = validate_config({"poll_interval_ms": 10})
        assert errors == []
        assert config is not None
        assert config.poll_interval_ms == 10


class TestValidateConfigErrorAccumulation:
    """Tests for error accumulation behavior."""

    def test_multiple_errors_accumulated(self, config_fixtures_path: Path) -> None:
        """Validate returns ALL errors, not just first."""
        with open(config_fixtures_path / "invalid_config_wrong_types.json") as f:
            config_dict = json.load(f)

        config, errors = validate_config(config_dict)

        assert config is None
        # Should have errors for simulation_mode, log_level, window_width,
        # window_height, poll_interval_ms
        assert len(errors) >= 4
