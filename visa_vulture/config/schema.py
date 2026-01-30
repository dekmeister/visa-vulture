"""Configuration schema and validation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AppConfig:
    """Application configuration."""

    simulation_mode: bool = False
    simulation_file: str = "simulation/instruments.yaml"
    log_file: str = "equipment_controller.log"
    log_level: str = "INFO"
    window_title: str = "VISA Vulture"
    window_width: int = 1200
    window_height: int = 800
    poll_interval_ms: int = 100


def validate_config(config_dict: dict[str, Any]) -> tuple[AppConfig | None, list[str]]:
    """
    Validate configuration dictionary and return AppConfig or list of errors.

    Returns:
        Tuple of (AppConfig or None, list of error messages)
    """
    errors: list[str] = []

    # Validate simulation_mode
    simulation_mode = config_dict.get("simulation_mode", False)
    if not isinstance(simulation_mode, bool):
        errors.append(
            f"simulation_mode must be boolean, got {type(simulation_mode).__name__}"
        )
        simulation_mode = False

    # Validate simulation_file
    simulation_file = config_dict.get("simulation_file", "simulation/instruments.yaml")
    if not isinstance(simulation_file, str):
        errors.append(
            f"simulation_file must be string, got {type(simulation_file).__name__}"
        )
        simulation_file = "simulation/instruments.yaml"

    # Validate log_file
    log_file = config_dict.get("log_file", "equipment_controller.log")
    if not isinstance(log_file, str):
        errors.append(f"log_file must be string, got {type(log_file).__name__}")
        log_file = "equipment_controller.log"

    # Validate log_level
    log_level = config_dict.get("log_level", "INFO")
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if not isinstance(log_level, str):
        errors.append(f"log_level must be string, got {type(log_level).__name__}")
        log_level = "INFO"
    elif log_level.upper() not in valid_levels:
        errors.append(f"log_level must be one of {valid_levels}, got '{log_level}'")
        log_level = "INFO"
    else:
        log_level = log_level.upper()

    # Validate window settings
    window_title = config_dict.get("window_title", "VISA Vulture")
    if not isinstance(window_title, str):
        errors.append(f"window_title must be string, got {type(window_title).__name__}")
        window_title = "VISA Vulture"

    window_width = config_dict.get("window_width", 1200)
    if not isinstance(window_width, int) or window_width < 400:
        errors.append(f"window_width must be integer >= 400, got {window_width}")
        window_width = 1200

    window_height = config_dict.get("window_height", 800)
    if not isinstance(window_height, int) or window_height < 300:
        errors.append(f"window_height must be integer >= 300, got {window_height}")
        window_height = 800

    # Validate poll_interval_ms
    poll_interval_ms = config_dict.get("poll_interval_ms", 100)
    if not isinstance(poll_interval_ms, int) or poll_interval_ms < 10:
        errors.append(f"poll_interval_ms must be integer >= 10, got {poll_interval_ms}")
        poll_interval_ms = 100

    if errors:
        return None, errors

    return (
        AppConfig(
            simulation_mode=simulation_mode,
            simulation_file=simulation_file,
            log_file=log_file,
            log_level=log_level,
            window_title=window_title,
            window_width=window_width,
            window_height=window_height,
            poll_interval_ms=poll_interval_ms,
        ),
        [],
    )
