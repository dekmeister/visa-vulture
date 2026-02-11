#!/usr/bin/env python3
"""VISA Vulture - Main entry point."""

import argparse
import logging
import sys
import tkinter as tk
from pathlib import Path

from .config import load_config
from .instruments import VISAConnection, scan_custom_instruments, build_instrument_registry
from .logging_config import setup_logging
from .model import EquipmentModel
from .presenter import EquipmentPresenter
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
        return (
            f"Invalid VISA backend '{backend}'. "
            f"Available backends: {available}"
        )


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load configuration
    config_path = args.config
    config, errors = load_config(config_path)

    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    if config is None:
        print("Failed to load configuration", file=sys.stderr)
        return 1

    # Override simulation mode if requested
    if args.simulation:
        config.simulation_mode = True

    # Validate VISA backend if specified and not in simulation mode
    if config.visa_backend and not config.simulation_mode:
        backend_error = validate_visa_backend(config.visa_backend)
        if backend_error:
            print(f"Configuration error: {backend_error}", file=sys.stderr)
            return 1

    # Setup logging
    gui_handler = setup_logging(
        log_file=config.log_file,
        log_level=config.log_level,
    )

    logger.info("Starting VISA Vulture")
    logger.info("Simulation mode: %s", config.simulation_mode)

    # Scan for custom instruments in the root instruments/ directory
    custom_instruments = scan_custom_instruments(Path.cwd() / "instruments")
    instrument_registry = build_instrument_registry(custom_instruments)
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

    # Create model
    model = EquipmentModel(visa_connection)

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

    view = MainWindow(
        root,
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
        instrument_registry=instrument_registry,
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
