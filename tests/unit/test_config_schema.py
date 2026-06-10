"""Tests for the config schema module."""

import json
from pathlib import Path

import pytest

from visa_vulture.config.schema import AppConfig, ValidationLimits, validate_config
from visa_vulture.model import validate_soft_limit_config


class TestAppConfig:
    """Tests for AppConfig dataclass."""

    def test_default_values(self) -> None:
        """AppConfig has correct default values."""
        config = AppConfig()
        assert config.simulation_mode is False
        assert config.simulation_file == "simulation/instruments.yaml"
        assert config.visa_backend == ""
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


class TestValidateConfigVisaBackend:
    """Tests for visa_backend validation."""

    def test_default_visa_backend_is_empty_string(self) -> None:
        """Default visa_backend is empty string (auto-detect)."""
        config, errors = validate_config({})
        assert errors == []
        assert config is not None
        assert config.visa_backend == ""

    def test_valid_visa_backend_string(self) -> None:
        """String visa_backend is accepted."""
        config, errors = validate_config({"visa_backend": "py"})
        assert errors == []
        assert config is not None
        assert config.visa_backend == "py"

    def test_empty_string_visa_backend_is_valid(self) -> None:
        """Empty string visa_backend (auto-detect) is valid."""
        config, errors = validate_config({"visa_backend": ""})
        assert errors == []
        assert config is not None
        assert config.visa_backend == ""

    def test_invalid_visa_backend_type_returns_error(self) -> None:
        """Non-string visa_backend returns error."""
        config, errors = validate_config({"visa_backend": 123})
        assert config is None
        assert any("visa_backend must be string" in e for e in errors)


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
    """Tests for validation_limits configuration (generic structure)."""

    def test_default_validation_limits(self) -> None:
        """Default config has typed common defaults and no instrument sections.

        Per-instrument-type defaults now live in the model descriptors, not in
        the config object, so instrument_limits is empty by default.
        """
        config, errors = validate_config({})

        assert errors == []
        assert config is not None
        assert config.validation_limits is not None
        assert config.validation_limits.common.duration_max_s == 86400.0
        assert config.validation_limits.instrument_limits == {}

    def test_custom_signal_generator_limits(self) -> None:
        """Custom signal generator limits are parsed into instrument_limits."""
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
        limits = config.validation_limits
        assert limits.get_limit("signal_generator", "power_min_dbm") == -80.0
        assert limits.get_limit("signal_generator", "power_max_dbm") == 20.0
        assert limits.get_limit("signal_generator", "frequency_min_hz") == 10.0
        assert limits.get_limit("signal_generator", "frequency_max_hz") == 10e9

    def test_custom_power_supply_limits(self) -> None:
        """Custom power supply limits are parsed into instrument_limits."""
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
        limits = config.validation_limits
        assert limits.get_limit("power_supply", "voltage_max_v") == 60.0
        assert limits.get_limit("power_supply", "current_max_a") == 30.0

    def test_custom_common_limits(self) -> None:
        """Custom common limits are parsed correctly (common stays typed)."""
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

    def test_partial_limits_only_store_provided_keys(self) -> None:
        """Unspecified keys are absent (defaults come from descriptors, not config)."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "power_min_dbm": -50,
                    # power_max_dbm not specified
                }
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        limits = config.validation_limits
        assert limits.get_limit("signal_generator", "power_min_dbm") == -50.0
        assert limits.get_limit("signal_generator", "power_max_dbm") is None

    def test_unknown_section_parsed_generically(self) -> None:
        """Unknown sections are parsed (numeric) without error at config level.

        Whether the section is meaningful is decided later by the registry-driven
        startup check (which warns), not by config schema validation.
        """
        config_dict = {
            "validation_limits": {
                "mystery_meter": {"some_key": 5},
            }
        }

        config, errors = validate_config(config_dict)

        assert errors == []
        assert config is not None
        assert config.validation_limits.get_limit("mystery_meter", "some_key") == 5.0

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

    def test_section_not_an_object_returns_error(self) -> None:
        """A non-object instrument section returns an error."""
        config_dict = {"validation_limits": {"signal_generator": 5}}

        config, errors = validate_config(config_dict)

        assert config is None
        assert any(
            "validation_limits.signal_generator must be an object" in e for e in errors
        )

    def test_negative_frequency_accepted_at_config_level(self) -> None:
        """Sign constraints are deferred to the registry-driven startup check."""
        config_dict = {
            "validation_limits": {
                "signal_generator": {
                    "frequency_min_hz": -1,
                }
            }
        }

        config, errors = validate_config(config_dict)

        # Numeric, so config validation passes; the >= 0 check happens at startup.
        assert errors == []
        assert config is not None
        assert config.validation_limits.get_limit("signal_generator", "frequency_min_hz") == -1.0

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
        value = config.validation_limits.get_limit("signal_generator", "power_min_dbm")
        assert isinstance(value, float)
        assert value == -100.0


class TestValidateSoftLimitConfig:
    """Tests for the registry-driven startup soft-limit validation."""

    def test_valid_limits_no_errors_or_warnings(self) -> None:
        limits = ValidationLimits(
            instrument_limits={
                "signal_generator": {"power_min_dbm": -90, "frequency_max_hz": 40e9},
                "power_supply": {"voltage_max_v": 50.0},
            }
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert errors == []
        assert warnings == []

    def test_negative_frequency_limit_is_error(self) -> None:
        limits = ValidationLimits(
            instrument_limits={"signal_generator": {"frequency_min_hz": -1.0}}
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert any("frequency_min_hz must be numeric >= 0" in e for e in errors)

    def test_negative_voltage_limit_is_error(self) -> None:
        limits = ValidationLimits(
            instrument_limits={"power_supply": {"voltage_max_v": -10.0}}
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert any("voltage_max_v must be numeric >= 0" in e for e in errors)

    def test_negative_power_limit_is_allowed(self) -> None:
        """Power (dBm) limits may be negative — no config_min constraint."""
        limits = ValidationLimits(
            instrument_limits={"signal_generator": {"power_min_dbm": -120.0}}
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert errors == []

    def test_unknown_section_warns(self) -> None:
        limits = ValidationLimits(
            instrument_limits={"mystery_meter": {"some_key": 5.0}}
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert errors == []
        assert any("mystery_meter" in w for w in warnings)

    def test_unknown_key_warns(self) -> None:
        """A typo'd key surfaces as a warning instead of being silently ignored."""
        limits = ValidationLimits(
            instrument_limits={"signal_generator": {"frequency_max_hzz": 50e9}}
        )
        errors, warnings = validate_soft_limit_config(limits)
        assert errors == []
        assert any("frequency_max_hzz" in w for w in warnings)
