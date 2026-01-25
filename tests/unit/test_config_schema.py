"""Tests for the config schema module."""

import json
from pathlib import Path

import pytest

from visa_vulture.config.schema import AppConfig, InstrumentConfig, validate_config


class TestInstrumentConfig:
    """Tests for InstrumentConfig dataclass."""

    def test_creation_with_required_fields(self) -> None:
        """InstrumentConfig can be created with required fields."""
        config = InstrumentConfig(
            name="Power Supply",
            resource_address="TCPIP::192.168.1.100::INSTR",
            type="power_supply",
        )
        assert config.name == "Power Supply"
        assert config.resource_address == "TCPIP::192.168.1.100::INSTR"
        assert config.type == "power_supply"

    def test_default_timeout_is_5000(self) -> None:
        """Default timeout_ms is 5000."""
        config = InstrumentConfig(
            name="PS",
            resource_address="TCPIP::1.2.3.4::INSTR",
            type="power_supply",
        )
        assert config.timeout_ms == 5000

    def test_custom_timeout(self) -> None:
        """Custom timeout_ms can be set."""
        config = InstrumentConfig(
            name="PS",
            resource_address="TCPIP::1.2.3.4::INSTR",
            type="power_supply",
            timeout_ms=10000,
        )
        assert config.timeout_ms == 10000


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
        assert config.instruments == []

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
        assert len(config.instruments) == 2

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
        assert config.instruments == []


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


class TestValidateConfigInstruments:
    """Tests for instruments list validation."""

    def test_instruments_not_list_returns_error(self) -> None:
        """Non-list instruments returns error."""
        config, errors = validate_config({"instruments": "power_supply"})
        assert config is None
        assert any("instruments must be a list" in e for e in errors)

    def test_instrument_not_dict_returns_error(self) -> None:
        """Non-dict instrument returns error."""
        config, errors = validate_config({"instruments": ["not_a_dict"]})
        assert config is None
        assert any("instruments[0] must be a dict" in e for e in errors)

    def test_instrument_missing_name_returns_error(self) -> None:
        """Missing name field returns error."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "resource_address": "TCPIP::1.2.3.4::INSTR",
                        "type": "power_supply",
                    }
                ]
            }
        )
        assert config is None
        assert any("name is required" in e for e in errors)

    def test_instrument_missing_resource_address_returns_error(self) -> None:
        """Missing resource_address field returns error."""
        config, errors = validate_config(
            {"instruments": [{"name": "PS", "type": "power_supply"}]}
        )
        assert config is None
        assert any("resource_address is required" in e for e in errors)

    def test_instrument_missing_type_returns_error(self) -> None:
        """Missing type field returns error."""
        config, errors = validate_config(
            {
                "instruments": [
                    {"name": "PS", "resource_address": "TCPIP::1.2.3.4::INSTR"}
                ]
            }
        )
        assert config is None
        assert any("type is required" in e for e in errors)

    def test_instrument_invalid_type_returns_error(
        self, config_fixtures_path: Path
    ) -> None:
        """Invalid instrument type returns error."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "name": "Scope",
                        "resource_address": "TCPIP::1.2.3.4::INSTR",
                        "type": "oscilloscope",
                    }
                ]
            }
        )
        assert config is None
        assert any("type must be one of" in e for e in errors)

    def test_instrument_timeout_below_minimum_returns_error(self) -> None:
        """timeout_ms below 100 returns error."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "name": "PS",
                        "resource_address": "TCPIP::1.2.3.4::INSTR",
                        "type": "power_supply",
                        "timeout_ms": 50,
                    }
                ]
            }
        )
        assert config is None
        assert any("timeout_ms must be integer >= 100" in e for e in errors)

    def test_instrument_timeout_non_integer_returns_error(self) -> None:
        """Non-integer timeout_ms returns error."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "name": "PS",
                        "resource_address": "TCPIP::1.2.3.4::INSTR",
                        "type": "power_supply",
                        "timeout_ms": "fast",
                    }
                ]
            }
        )
        assert config is None
        assert any("timeout_ms must be integer >= 100" in e for e in errors)

    def test_valid_power_supply_instrument(self) -> None:
        """Valid power_supply instrument is accepted."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "name": "Power Supply",
                        "resource_address": "TCPIP::192.168.1.100::INSTR",
                        "type": "power_supply",
                    }
                ]
            }
        )
        assert errors == []
        assert config is not None
        assert len(config.instruments) == 1
        assert config.instruments[0].type == "power_supply"

    def test_valid_signal_generator_instrument(self) -> None:
        """Valid signal_generator instrument is accepted."""
        config, errors = validate_config(
            {
                "instruments": [
                    {
                        "name": "Signal Generator",
                        "resource_address": "TCPIP::192.168.1.101::INSTR",
                        "type": "signal_generator",
                    }
                ]
            }
        )
        assert errors == []
        assert config is not None
        assert len(config.instruments) == 1
        assert config.instruments[0].type == "signal_generator"


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

    def test_multiple_instrument_errors_accumulated(
        self, config_fixtures_path: Path
    ) -> None:
        """Multiple instrument errors are accumulated."""
        with open(
            config_fixtures_path / "invalid_config_missing_instrument_fields.json"
        ) as f:
            config_dict = json.load(f)

        config, errors = validate_config(config_dict)

        assert config is None
        # Should have errors for each invalid instrument
        assert len(errors) >= 3
