"""Configuration loading from JSON files."""

import json
import logging
from pathlib import Path

from .schema import AppConfig, validate_config

logger = logging.getLogger(__name__)


def load_config(
    config_path: str | Path | None = None,
) -> tuple[AppConfig | None, list[str]]:
    """
    Load configuration from JSON file.

    Args:
        config_path: Path to config file. If None, uses default_config.json.

    Returns:
        Tuple of (AppConfig or None, list of error messages)
    """
    errors: list[str] = []

    # Determine config file path
    if config_path is None:
        config_path = Path(__file__).parent / "default_config.json"
    else:
        config_path = Path(config_path)

    # Check file exists
    if not config_path.exists():
        errors.append(f"Configuration file not found: {config_path}")
        return None, errors

    # Load JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in configuration file: {e}")
        return None, errors
    except OSError as e:
        errors.append(f"Error reading configuration file: {e}")
        return None, errors

    if not isinstance(config_dict, dict):
        errors.append(
            f"Configuration must be a JSON object, got {type(config_dict).__name__}"
        )
        return None, errors

    # Validate and return
    config, validation_errors = validate_config(config_dict)
    errors.extend(validation_errors)

    if errors:
        return None, errors

    logger.info("Configuration loaded from %s", config_path)
    return config, []
