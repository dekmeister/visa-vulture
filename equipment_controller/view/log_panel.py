"""Log panel widget for displaying application logs."""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable


class LogPanel(ttk.Frame):
    """
    Scrolling text panel for log display with level filtering.

    Displays log messages with color coding by level and
    provides a filter dropdown to show only certain levels.
    """

    # Color scheme for log levels
    LEVEL_COLORS = {
        "DEBUG": "#808080",  # Gray
        "INFO": "#000000",  # Black
        "WARNING": "#FF8C00",  # Dark Orange
        "ERROR": "#FF0000",  # Red
        "CRITICAL": "#8B0000",  # Dark Red
    }

    LEVEL_TAGS = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize log panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._min_level = logging.DEBUG
        self._auto_scroll = True
        self._log_records: list[logging.LogRecord] = []

        self._create_widgets()
        self._configure_tags()

    def _create_widgets(self) -> None:
        """Create child widgets."""
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=2, pady=2)

        # Level filter
        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))

        self._level_var = tk.StringVar(value="DEBUG")
        self._level_combo = ttk.Combobox(
            toolbar,
            textvariable=self._level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=10,
        )
        self._level_combo.pack(side=tk.LEFT)
        self._level_combo.bind("<<ComboboxSelected>>", self._on_filter_changed)

        # Auto-scroll checkbox
        self._auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            toolbar,
            text="Auto-scroll",
            variable=self._auto_scroll_var,
            command=self._on_auto_scroll_changed,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Clear button
        ttk.Button(toolbar, text="Clear", command=self.clear).pack(side=tk.RIGHT)

        # Text widget with scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._scrollbar = ttk.Scrollbar(text_frame)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            yscrollcommand=self._scrollbar.set,
            font=("Consolas", 9),
        )
        self._text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._scrollbar.config(command=self._text.yview)

    def _configure_tags(self) -> None:
        """Configure text tags for log levels."""
        for level_name, color in self.LEVEL_COLORS.items():
            self._text.tag_configure(level_name, foreground=color)

    def _on_filter_changed(self, event=None) -> None:
        """Handle filter level change."""
        level_name = self._level_var.get()
        self._min_level = getattr(logging, level_name, logging.DEBUG)
        self._refresh_display()

    def _on_auto_scroll_changed(self) -> None:
        """Handle auto-scroll toggle."""
        self._auto_scroll = self._auto_scroll_var.get()
        if self._auto_scroll:
            self._text.see(tk.END)

    def append_record(self, record: logging.LogRecord) -> None:
        """
        Append a log record to the panel.

        Thread-safe: schedules update on main thread.

        Args:
            record: Log record to display
        """
        self._log_records.append(record)

        if record.levelno >= self._min_level:
            self._append_formatted(record)

    def _append_formatted(self, record: logging.LogRecord) -> None:
        """Append formatted record to text widget."""
        # Format the message
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )
        message = formatter.format(record) + "\n"

        # Get tag for level
        tag = self.LEVEL_TAGS.get(record.levelno, "INFO")

        # Update text widget
        self._text.config(state=tk.NORMAL)
        self._text.insert(tk.END, message, tag)
        self._text.config(state=tk.DISABLED)

        # Auto-scroll
        if self._auto_scroll:
            self._text.see(tk.END)

    def _refresh_display(self) -> None:
        """Refresh display with current filter."""
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)

        for record in self._log_records:
            if record.levelno >= self._min_level:
                self._append_formatted(record)

    def clear(self) -> None:
        """Clear all log entries."""
        self._log_records.clear()
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)

    def get_log_handler_callback(self) -> Callable[[logging.LogRecord], None]:
        """
        Get a callback function for use with GUILogHandler.

        The returned function schedules updates on the main thread.

        Returns:
            Callback function that accepts log records
        """

        def callback(record: logging.LogRecord) -> None:
            # Schedule on main thread
            self.after(0, lambda: self.append_record(record))

        return callback
