"""Log panel widget for displaying application logs."""

import logging
import threading
import tkinter as tk
from collections import deque
from tkinter import ttk
from typing import Callable


class LogPanel(ttk.Frame):
    """
    Scrolling text panel for log display with level filtering.

    Displays log messages with color coding by level and
    provides a filter dropdown to show only certain levels.

    Log records are buffered and flushed to the display periodically
    to avoid overwhelming the Tkinter event loop during high-volume logging.
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

    _MAX_LOG_RECORDS = 10_000
    _FLUSH_INTERVAL_MS = 100

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

        self._pending_records: deque[logging.LogRecord] = deque()
        self._pending_lock = threading.Lock()
        self._flush_timer_id: str | None = None

        self._formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )

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

    def start_flush_timer(self) -> None:
        """Start the periodic flush timer for batched log display."""
        self._schedule_flush()

    def stop_flush_timer(self) -> None:
        """Stop the periodic flush timer."""
        if self._flush_timer_id is not None:
            self.after_cancel(self._flush_timer_id)
            self._flush_timer_id = None

    def _schedule_flush(self) -> None:
        """Schedule the next flush."""
        self._flush_timer_id = self.after(
            self._FLUSH_INTERVAL_MS, self._flush_pending
        )

    def _flush_pending(self) -> None:
        """Flush all pending log records to the display in a single batch."""
        with self._pending_lock:
            records = list(self._pending_records)
            self._pending_records.clear()

        if records:
            self._log_records.extend(records)

            # Trim old records if over limit
            if len(self._log_records) > self._MAX_LOG_RECORDS:
                excess = len(self._log_records) - self._MAX_LOG_RECORDS
                del self._log_records[:excess]
                self._refresh_display()
            else:
                # Insert only the new visible records
                visible = [r for r in records if r.levelno >= self._min_level]
                if visible:
                    self._text.config(state=tk.NORMAL)
                    for record in visible:
                        message = self._formatter.format(record) + "\n"
                        tag = self.LEVEL_TAGS.get(record.levelno, "INFO")
                        self._text.insert(tk.END, message, tag)
                    self._text.config(state=tk.DISABLED)

                    if self._auto_scroll:
                        self._text.see(tk.END)

        self._schedule_flush()

    def _refresh_display(self) -> None:
        """Refresh display with current filter."""
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        for record in self._log_records:
            if record.levelno >= self._min_level:
                message = self._formatter.format(record) + "\n"
                tag = self.LEVEL_TAGS.get(record.levelno, "INFO")
                self._text.insert(tk.END, message, tag)
        self._text.config(state=tk.DISABLED)

        if self._auto_scroll:
            self._text.see(tk.END)

    def clear(self) -> None:
        """Clear all log entries."""
        with self._pending_lock:
            self._pending_records.clear()
        self._log_records.clear()
        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.config(state=tk.DISABLED)

    def get_log_handler_callback(self) -> Callable[[logging.LogRecord], None]:
        """
        Get a callback function for use with GUILogHandler.

        Records are buffered and flushed to the display periodically
        to avoid overwhelming the Tkinter event loop.

        Returns:
            Callback function that accepts log records
        """

        def callback(record: logging.LogRecord) -> None:
            with self._pending_lock:
                self._pending_records.append(record)

        return callback
