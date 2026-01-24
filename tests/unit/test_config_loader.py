"""Tests for the config loader module."""

import json
from pathlib import Path

import pytest

from src.config.loader import load_config


class TestLoadConfigFile:
    """Tests for load_config with file handling."""

    def test_load_valid_config_file(self, config_fixtures_path: Path) -> None:
        """Loading valid config file returns AppConfig."""
        config_path = config_fixtures_path / "valid_config.json"
        config, errors = load_config(config_path)

        assert errors == []
        assert config is not None
        assert config.simulation_mode is True
        assert len(config.instruments) == 2

    def test_file_not_found_returns_error(self, tmp_path: Path) -> None:
        """Non-existent file returns error."""
        config_path = tmp_path / "nonexistent.json"
        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_invalid_json_returns_error(self, tmp_path: Path) -> None:
        """Invalid JSON syntax returns error."""
        config_path = tmp_path / "bad.json"
        config_path.write_text("{not valid json}")

        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_json_not_object_returns_error(self, tmp_path: Path) -> None:
        """JSON array instead of object returns error."""
        config_path = tmp_path / "array.json"
        config_path.write_text('["item1", "item2"]')

        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) == 1
        assert "must be a JSON object" in errors[0]

    def test_json_primitive_returns_error(self, tmp_path: Path) -> None:
        """JSON primitive instead of object returns error."""
        config_path = tmp_path / "primitive.json"
        config_path.write_text('"just a string"')

        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) == 1
        assert "must be a JSON object" in errors[0]


class TestLoadConfigValidation:
    """Tests for load_config validation error propagation."""

    def test_validation_errors_propagated(self, tmp_path: Path) -> None:
        """Validation errors from schema are returned."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text(json.dumps({"log_level": "INVALID_LEVEL"}))

        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) >= 1
        assert any("log_level" in e for e in errors)

    def test_multiple_validation_errors_returned(self, tmp_path: Path) -> None:
        """Multiple validation errors are all returned."""
        config_path = tmp_path / "multi_error.json"
        config_path.write_text(
            json.dumps(
                {
                    "simulation_mode": "not_a_bool",
                    "log_level": "INVALID",
                    "window_width": 100,
                }
            )
        )

        config, errors = load_config(config_path)

        assert config is None
        assert len(errors) >= 3


class TestLoadConfigDefaultPath:
    """Tests for load_config default path behavior."""

    def test_none_path_uses_default_config(self) -> None:
        """None path uses default_config.json from config directory."""
        # This tests that passing None doesn't crash and uses the default
        # The default config should exist and be valid
        config, errors = load_config(None)

        # Default config should load without errors
        assert errors == []
        assert config is not None


class TestLoadConfigPathTypes:
    """Tests for load_config with different path types."""

    def test_string_path_works(self, config_fixtures_path: Path) -> None:
        """String path is accepted."""
        config_path = str(config_fixtures_path / "valid_config.json")
        config, errors = load_config(config_path)

        assert errors == []
        assert config is not None

    def test_path_object_works(self, config_fixtures_path: Path) -> None:
        """Path object is accepted."""
        config_path = config_fixtures_path / "valid_config.json"
        config, errors = load_config(config_path)

        assert errors == []
        assert config is not None


class TestLoadConfigMinimalConfig:
    """Tests for load_config with minimal configuration."""

    def test_minimal_config_uses_defaults(
        self, config_fixtures_path: Path
    ) -> None:
        """Minimal config (empty object) uses all defaults."""
        config_path = config_fixtures_path / "valid_config_minimal.json"
        config, errors = load_config(config_path)

        assert errors == []
        assert config is not None
        assert config.simulation_mode is False
        assert config.log_level == "INFO"
        assert config.window_width == 1200
        assert config.window_height == 800
