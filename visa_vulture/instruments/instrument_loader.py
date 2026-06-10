"""Instrument loading, auto-scanning, and custom instrument support."""

import importlib.util
import inspect
import logging
import sys
import types
from dataclasses import dataclass
from pathlib import Path

from .base_instrument import BaseInstrument

logger = logging.getLogger(__name__)

# Maps base classes to their instrument_type strings. Supplied by the caller
# (main.py derives it from the model registry) so this package never names
# concrete instrument types and cannot form an import cycle with the model.
BaseTypeMap = dict[type[BaseInstrument], str]


@dataclass
class InstrumentEntry:
    """Registry entry for an instrument type."""

    cls: type[BaseInstrument]
    display_name: str
    instrument_type: str
    is_builtin: bool = False


def scan_custom_instruments(
    instruments_dir: Path,
    base_type_map: BaseTypeMap,
) -> dict[str, InstrumentEntry]:
    """
    Scan a directory for custom instrument modules.

    Discovers classes that extend one of the supplied base instrument types and
    have a ``display_name`` class attribute. Classes that extend BaseInstrument
    directly are rejected with a warning.

    Args:
        instruments_dir: Path to the directory to scan
        base_type_map: Maps each built-in base class to its instrument_type
            string. A custom class must subclass one of these.

    Returns:
        Dictionary mapping display_name to InstrumentEntry
    """
    registry: dict[str, InstrumentEntry] = {}

    if not instruments_dir.is_dir():
        logger.debug("Custom instruments directory not found: %s", instruments_dir)
        return registry

    for py_file in sorted(instruments_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        module_name = py_file.stem

        try:
            module = _load_module_from_file(module_name, py_file)
        except Exception as e:
            logger.warning(
                "Failed to import custom instrument module '%s': %s",
                py_file,
                e,
            )
            continue

        # Inspect all classes defined in this module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip classes not defined in this module
            if obj.__module__ != module.__name__:
                continue

            # Skip classes without display_name
            display_name = getattr(obj, "display_name", None)
            if not isinstance(display_name, str):
                continue

            # Reject direct BaseInstrument subclasses
            if BaseInstrument in obj.__bases__:
                logger.warning(
                    "Custom instrument '%s' in '%s' extends BaseInstrument "
                    "directly. Custom instruments must extend a built-in "
                    "instrument type. Skipping.",
                    name,
                    py_file.name,
                )
                continue

            # Determine base type from the supplied base map
            instrument_type = _get_base_type(obj, base_type_map)
            if instrument_type is None:
                logger.warning(
                    "Custom instrument '%s' in '%s' does not extend a known "
                    "built-in instrument type. Skipping.",
                    name,
                    py_file.name,
                )
                continue

            entry = InstrumentEntry(
                cls=obj,
                display_name=display_name,
                instrument_type=instrument_type,
                is_builtin=False,
            )
            registry[display_name] = entry
            logger.info(
                "Discovered custom instrument: %s (%s) from %s",
                display_name,
                instrument_type,
                py_file.name,
            )

    return registry


def build_instrument_registry(
    builtins: dict[str, InstrumentEntry],
    custom: dict[str, InstrumentEntry] | None = None,
) -> dict[str, InstrumentEntry]:
    """
    Build the complete instrument registry from built-in and custom entries.

    Args:
        builtins: Built-in instrument entries (main.py derives these from the
            model's instrument-type registry).
        custom: Custom instruments discovered by scan_custom_instruments.

    Returns:
        Complete registry mapping display_name to InstrumentEntry
    """
    registry: dict[str, InstrumentEntry] = dict(builtins)

    if custom:
        registry.update(custom)

    return registry


def create_instrument(
    registry: dict[str, InstrumentEntry],
    display_name: str,
    resource_address: str,
    timeout_ms: int = 5000,
) -> BaseInstrument:
    """
    Create an instrument instance from the registry.

    Args:
        registry: Instrument registry from build_instrument_registry
        display_name: Display name key to look up in registry
        resource_address: VISA resource address
        timeout_ms: Communication timeout in milliseconds

    Returns:
        Instrument instance

    Raises:
        ValueError: If display_name is not found in registry
    """
    if display_name not in registry:
        raise ValueError(f"Unknown instrument: {display_name}")

    entry = registry[display_name]
    return entry.cls(entry.display_name, resource_address, timeout_ms)


def _load_module_from_file(module_name: str, file_path: Path) -> types.ModuleType:
    """
    Load a Python module directly from a file path.

    Uses importlib.util to load from a specific file, avoiding sys.path
    manipulation and module cache conflicts.

    Args:
        module_name: Name to assign to the loaded module
        file_path: Path to the .py file

    Returns:
        The loaded module

    Raises:
        ImportError: If the module cannot be loaded
    """
    qualified_name = f"_custom_instruments.{module_name}"
    spec = importlib.util.spec_from_file_location(qualified_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


def _get_base_type(cls: type, base_type_map: BaseTypeMap) -> str | None:
    """
    Determine the instrument_type for a class from the supplied base map.

    Returns:
        The matching instrument_type string, or None if ``cls`` is not a
        subclass of any base class in ``base_type_map``.
    """
    for base_cls, type_str in base_type_map.items():
        if issubclass(cls, base_cls):
            return type_str
    return None
