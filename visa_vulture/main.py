#!/usr/bin/env python3
"""VISA Vulture - Main entry point."""

import argparse
import logging
import sys
import tkinter as tk
from tkinter import messagebox

from .config import load_config
from .instruments import (
    InstrumentEntry,
    VISAConnection,
    scan_custom_instruments,
    build_instrument_catalog,
)
from .logging_config import setup_logging
from .model import (
    INSTRUMENT_TYPE_REGISTRY,
    EquipmentModel,
    validate_soft_limit_config,
)
from .presenter import EquipmentPresenter
from .utils import is_frozen, resolve_custom_instruments_dir, resolve_log_file
from .view import DisclaimerDialog, MainWindow

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="VISA Vulture - VISA Test Equipment Control Application"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: config/default_config.json)",
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Force simulation mode (overrides config)",
    )
    return parser.parse_args()


def validate_visa_backend(backend: str) -> str | None:
    """Validate that a VISA backend is installed.

    Args:
        backend: Backend name (e.g. "ivi", "py")

    Returns:
        Error message if invalid, None if valid.
    """
    from pyvisa.highlevel import get_wrapper_class, list_backends

    try:
        get_wrapper_class(backend)
        return None
    except ValueError:
        available = list_backends()
        return f"Invalid VISA backend '{backend}'. " f"Available backends: {available}"


def _should_show_error_dialog() -> bool:
    """Return True when stderr output would not be seen by the user.

    That is the case for a packaged executable (typically launched from a
    shortcut, with no console attached) or whenever stderr is unavailable.
    """
    return is_frozen() or sys.stderr is None


def report_startup_errors(heading: str, errors: list[str]) -> None:
    """Report errors that prevent the application from starting.

    Always writes to stderr when available. Additionally shows a modal error
    dialog when there is no console for the user to read stderr from.

    Args:
        heading: One-line summary, e.g. "Configuration errors"
        errors: Individual error messages (may be empty)
    """
    if errors:
        lines = [f"{heading}:"] + [f"  - {e}" for e in errors]
    else:
        lines = [heading]
    message = "\n".join(lines)

    if sys.stderr is not None:
        print(message, file=sys.stderr)

    if not _should_show_error_dialog():
        return

    try:
        root = tk.Tk()
    except tk.TclError:
        # No display available; nothing more we can do.
        return
    try:
        root.withdraw()
        messagebox.showerror("VISA Vulture - startup error", message, parent=root)
    finally:
        root.destroy()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load configuration
    config_path = args.config
    config, errors = load_config(config_path)

    if errors:
        report_startup_errors("Configuration errors", errors)
        return 1

    if config is None:
        report_startup_errors("Failed to load configuration", [])
        return 1

    # Override simulation mode if requested
    if args.simulation:
        config.simulation_mode = True

    # Validate VISA backend if specified and not in simulation mode
    if config.visa_backend and not config.simulation_mode:
        backend_error = validate_visa_backend(config.visa_backend)
        if backend_error:
            report_startup_errors("Configuration errors", [backend_error])
            return 1

    # Setup logging
    log_file = resolve_log_file(config.log_file)
    gui_handler = setup_logging(
        log_file=log_file,
        log_level=config.log_level,
    )

    logger.info("Starting VISA Vulture")
    logger.info("Logging to %s", log_file.resolve())
    logger.info("Simulation mode: %s", config.simulation_mode)

    # Validate configured soft limits against the instrument-type registry.
    # Unknown sections/keys warn (e.g. typos); constraint violations block launch.
    limit_errors, limit_warnings = validate_soft_limit_config(config.validation_limits)
    for warning in limit_warnings:
        logger.warning("Configuration warning: %s", warning)
    if limit_errors:
        report_startup_errors("Configuration errors", limit_errors)
        return 1

    # Derive the loader's base-type map and built-in entries from the model's
    # instrument-type registry, so the instruments package never names types.
    base_type_map = {
        d.instrument_cls: d.instrument_type for d in INSTRUMENT_TYPE_REGISTRY.values()
    }
    builtin_entries = {
        d.display_name: InstrumentEntry(
            cls=d.instrument_cls,
            display_name=d.display_name,
            instrument_type=d.instrument_type,
            is_builtin=True,
        )
        for d in INSTRUMENT_TYPE_REGISTRY.values()
    }

    # Scan for custom instruments in the instruments/ directory (working
    # directory when run from source, next to the executable when frozen)
    custom_instruments_dir = resolve_custom_instruments_dir()
    logger.debug("Custom instruments directory: %s", custom_instruments_dir)
    custom_instruments = scan_custom_instruments(custom_instruments_dir, base_type_map)
    instrument_catalog = build_instrument_catalog(builtin_entries, custom_instruments)
    if custom_instruments:
        logger.info(
            "Loaded %d custom instrument(s): %s",
            len(custom_instruments),
            ", ".join(custom_instruments.keys()),
        )

    # Create VISA connection
    visa_connection = VISAConnection(
        simulation_mode=config.simulation_mode,
        simulation_file=config.simulation_file,
        visa_backend=config.visa_backend,
    )
    logger.info("VISA backend: %s", visa_connection.active_backend)

    # Create model (driven by the same instrument-type registry the loader and
    # view specs are derived from)
    model = EquipmentModel(visa_connection, instrument_types=INSTRUMENT_TYPE_REGISTRY)

    # Create GUI
    root = tk.Tk()
    root.withdraw()

    # Show safety disclaimer - exit if user declines
    disclaimer = DisclaimerDialog(root)
    if not disclaimer.show():
        logger.info("User declined disclaimer, exiting")
        root.destroy()
        return 0

    root.deiconify()

    # Derive the per-type view specs from the model's descriptor registry so the
    # view can build one tab per instrument type without importing the model.
    instrument_view_specs = {t: d.view for t, d in INSTRUMENT_TYPE_REGISTRY.items()}

    view = MainWindow(
        root,
        instrument_view_specs=instrument_view_specs,
        title=config.window_title,
        width=config.window_width,
        height=config.window_height,
        visa_backend_label=visa_connection.active_backend,
    )

    # Wire GUI log handler
    gui_handler.set_callback(view.log_panel.get_log_handler_callback())
    view.log_panel.start_flush_timer()

    # Create presenter
    presenter = EquipmentPresenter(
        model=model,
        view=view,
        poll_interval_ms=config.poll_interval_ms,
        plot_refresh_interval_ms=config.plot_refresh_interval_ms,
        validation_limits=config.validation_limits,
        instrument_catalog=instrument_catalog,
    )

    # Setup clean shutdown
    def on_closing():
        logger.info("Application closing")
        view.log_panel.stop_flush_timer()
        presenter.shutdown()
        visa_connection.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Run application
    logger.info("Entering main loop")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        on_closing()

    logger.info("Application exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
