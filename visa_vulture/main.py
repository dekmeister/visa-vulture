#!/usr/bin/env python3
"""VISA Vulture - Main entry point."""

import argparse
import logging
import sys
import tkinter as tk
from pathlib import Path

from .config import load_config
from .instruments import VISAConnection
from .logging_config import setup_logging
from .model import EquipmentModel
from .presenter import EquipmentPresenter
from .view import MainWindow

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

    # Setup logging
    gui_handler = setup_logging(
        log_file=config.log_file,
        log_level=config.log_level,
    )

    logger.info("Starting VISA Vulture")
    logger.info("Simulation mode: %s", config.simulation_mode)

    # Create VISA connection
    visa_connection = VISAConnection(
        simulation_mode=config.simulation_mode,
        simulation_file=config.simulation_file,
    )

    # Create model
    model = EquipmentModel(visa_connection)

    # Create GUI
    root = tk.Tk()

    view = MainWindow(
        root,
        title=config.window_title,
        width=config.window_width,
        height=config.window_height,
    )

    # Wire GUI log handler
    gui_handler.set_callback(view.log_panel.get_log_handler_callback())
    view.log_panel.start_flush_timer()

    # Create presenter
    presenter = EquipmentPresenter(
        model=model,
        view=view,
        poll_interval_ms=config.poll_interval_ms,
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
