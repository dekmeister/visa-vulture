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


class TestValidateConfigIntegerMinFields:
    """Tests for integer fields with minimum value constraints."""

    @pytest.mark.parametrize(
        "field,minimum,below_value",
        [
            ("window_width", 400, 300),
            ("window_height", 300, 200),
            ("poll_interval_ms", 10, 5),
        ],
    )
    def test_below_minimum_returns_error(
        self, field: str, minimum: int, below_value: int
    ) -> None:
        """Value below minimum returns error."""
        config, errors = validate_config({field: below_value})
        assert config is None
        assert any(f"{field} must be integer >= {minimum}" in e for e in errors)

    @pytest.mark.parametrize(
        "field,minimum,bad_value",
        [
            ("window_width", 400, "wide"),
            ("window_height", 300, "tall"),
            ("poll_interval_ms", 10, "fast"),
        ],
    )
    def test_non_integer_returns_error(
        self, field: str, minimum: int, bad_value: str
    ) -> None:
        """Non-integer value returns error."""
        config, errors = validate_config({field: bad_value})
        assert config is None
        assert any(f"{field} must be integer >= {minimum}" in e for e in errors)

    @pytest.mark.parametrize(
        "field,min_value",
        [
            ("window_width", 400),
            ("window_height", 300),
            ("poll_interval_ms", 10),
        ],
    )
    def test_at_minimum_is_valid(self, field: str, min_value: int) -> None:
        """Value at exactly the minimum is accepted."""
        config, errors = validate_config({field: min_value})
        assert errors == []
        assert config is not None
        assert getattr(config, field) == min_value


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


class TestValidationLimitsConfig:
    """Tests for validation_limits configuration."""

    def test_default_validation_limits(self) -> None:
        """Default config includes sensible validation limits."""
        config, errors = validate_config({})

        assert errors == []
        assert config is not None
        assert config.validation_limits is not None

        # Check signal generator defaults
        assert config.validation_limits.signal_generator.power_min_dbm == -100.0
        assert config.validation_limits.signal_generator.power_max_dbm == 30.0
        assert config.validation_limits.signal_generator.frequency_min_hz == 1.0
        assert config.validation_limits.signal_generator.frequency_max_hz == 50e9

        # Check power supply defaults
        assert config.validation_limits.power_supply.voltage_max_v == 100.0
        assert config.validation_limits.power_supply.current_max_a == 50.0

        # Check common defaults
        assert config.validation_limits.common.duration_max_s == 86400.0

    def test_custom_signal_generator_limits(self) -> None:
        """Custom signal generator limits are parsed correctly."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "power_min_dbm": -80,
                    "power_max_dbm": 20,
                    "frequency_min_hz": 10,
                    "frequency_max_hz": 10000000000,
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.validation_limits.signal_generator.power_min_dbm == -80.0
        assert config.validation_limits.signal_generator.power_max_dbm == 20.0
        assert config.validation_limits.signal_generator.frequency_min_hz == 10.0
        assert config.validation_limits.signal_generator.frequency_max_hz == 10e9

    def test_custom_power_supply_limits(self) -> None:
        """Custom power supply limits are parsed correctly."""
        config_dict = {
            "validation_limits": {
                "power_supply": {
                    "voltage_max_v": 60,
                    "current_max_a": 30,
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.validation_limits.power_supply.voltage_max_v == 60.0
        assert config.validation_limits.power_supply.current_max_a == 30.0

    def test_custom_common_limits(self) -> None:
        """Custom common limits are parsed correctly."""
        config_dict = {
            "validation_limits": {
                "common": {
                    "duration_max_s": 3600,  # 1 hour
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.validation_limits.common.duration_max_s == 3600.0

    def test_partial_limits_use_defaults(self) -> None:
        """Partially specified limits fill in defaults."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "power_min_dbm": -50,
                    # power_max_dbm not specified - should use default
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.validation_limits.signal_generator.power_min_dbm == -50.0
        assert config.validation_limits.signal_generator.power_max_dbm == 30.0  # default

    def test_invalid_limit_type_returns_error(self) -> None:
        """Non-numeric limit values return error."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "power_min_dbm": "low",
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert config is None
        assert any("power_min_dbm must be numeric" in e for e in errors)

    def test_negative_frequency_limit_returns_error(self) -> None:
        """Negative frequency limit returns error."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "frequency_min_hz": -1,
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert config is None
        assert any("frequency_min_hz must be numeric >= 0" in e for e in errors)

    def test_negative_voltage_limit_returns_error(self) -> None:
        """Negative voltage limit returns error."""
        config_dict = {
            "validation_limits": {
                "power_supply": {
                    "voltage_max_v": -10,
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert config is None
        assert any("voltage_max_v must be numeric >= 0" in e for e in errors)

    def test_zero_duration_limit_returns_error(self) -> None:
        """Zero duration limit returns error (must be > 0)."""
        config_dict = {
            "validation_limits": {
                "common": {
                    "duration_max_s": 0,
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert config is None
        assert any("duration_max_s must be numeric > 0" in e for e in errors)

    def test_integer_limits_converted_to_float(self) -> None:
        """Integer limit values are converted to float."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "power_min_dbm": -100,  # int, not float
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert isinstance(config.validation_limits.signal_generator.power_min_dbm, float)
        assert config.validation_limits.signal_generator.power_min_dbm == -100.0
