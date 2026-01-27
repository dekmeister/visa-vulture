"""Test points table widget for displaying test plan steps."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Sequence, Union
from enum import Enum


class InstrumentType(Enum):
    """Instrument type for table column configuration."""

    POWER_SUPPLY = "power_supply"
    SIGNAL_GENERATOR = "signal_generator"


class TestPointsTable(ttk.Frame):
    """
    Scrollable table displaying test plan steps with row highlighting.

    Supports both Power Supply and Signal Generator column layouts.
    """

    # Column configurations: (column_id, heading, width)
    COLUMNS = {
        InstrumentType.POWER_SUPPLY: [
            ("step", "Step", 50),
            ("duration", "Duration (s)", 80),
            ("abs_time", "Abs. Time (s)", 80),
            ("voltage", "Voltage (V)", 80),
            ("current", "Current (A)", 80),
            ("description", "Description", 150),
        ],
        InstrumentType.SIGNAL_GENERATOR: [
            ("step", "Step", 50),
            ("duration", "Duration (s)", 80),
            ("abs_time", "Abs. Time (s)", 80),
            ("frequency", "Frequency", 90),
            ("power", "Power (dBm)", 80),
            ("description", "Description", 150),
        ],
    }

    # Highlight color for current step
    HIGHLIGHT_BG = "#FFE4B5"  # Moccasin - soft orange

    def __init__(
        self,
        parent: tk.Widget,
        instrument_type: InstrumentType = InstrumentType.POWER_SUPPLY,
        **kwargs,
    ):
        """
        Initialize test points table.

        Args:
            parent: Parent widget
            instrument_type: Type of instrument (determines columns)
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._instrument_type = instrument_type
        self._step_to_item: dict[int, str] = {}
        self._current_step: int | None = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create Treeview and scrollbars."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Get column configuration
        columns = self.COLUMNS[self._instrument_type]
        column_ids = [col[0] for col in columns]

        # Create Treeview
        self._tree = ttk.Treeview(
            self,
            columns=column_ids,
            show="headings",
            selectmode="browse",
        )
        self._tree.grid(row=0, column=0, sticky="nsew")

        # Configure columns
        for col_id, heading, width in columns:
            self._tree.heading(col_id, text=heading)
            self._tree.column(col_id, width=width, minwidth=40, anchor=tk.CENTER)

        # Description column should be left-aligned and expandable
        self._tree.column("description", anchor=tk.W, stretch=True)

        # Vertical scrollbar
        v_scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=v_scroll.set)

        # Configure highlight tag
        self._tree.tag_configure("current", background=self.HIGHLIGHT_BG)

    def load_steps(self, steps: Sequence) -> None:
        """
        Load test steps into the table.

        Args:
            steps: Sequence of TestStep or SignalGeneratorTestStep objects
        """
        self.clear()

        for step in steps:
            item_id = f"step_{step.step_number}"
            self._step_to_item[step.step_number] = item_id

            if self._instrument_type == InstrumentType.POWER_SUPPLY:
                values = (
                    step.step_number,
                    f"{step.duration_seconds:.1f}",
                    f"{step.absolute_time_seconds:.1f}",
                    f"{step.voltage:.2f}",
                    f"{step.current:.2f}",
                    step.description,
                )
            else:  # Signal Generator
                # Format frequency with appropriate units
                freq = step.frequency
                if freq >= 1e9:
                    freq_str = f"{freq / 1e9:.3f} GHz"
                elif freq >= 1e6:
                    freq_str = f"{freq / 1e6:.3f} MHz"
                elif freq >= 1e3:
                    freq_str = f"{freq / 1e3:.3f} kHz"
                else:
                    freq_str = f"{freq:.1f} Hz"

                values = (
                    step.step_number,
                    f"{step.duration_seconds:.1f}",
                    f"{step.absolute_time_seconds:.1f}",
                    freq_str,
                    f"{step.power:.1f}",
                    step.description,
                )

            self._tree.insert("", tk.END, iid=item_id, values=values)

    def highlight_step(self, step_number: int) -> None:
        """
        Highlight the specified step row and scroll to make it visible.

        Args:
            step_number: 1-based step number to highlight
        """
        # Clear previous highlight
        if self._current_step is not None:
            prev_item = self._step_to_item.get(self._current_step)
            if prev_item and self._tree.exists(prev_item):
                self._tree.item(prev_item, tags=())

        # Apply new highlight
        item_id = self._step_to_item.get(step_number)
        if item_id and self._tree.exists(item_id):
            self._tree.item(item_id, tags=("current",))
            self._tree.see(item_id)
            self._current_step = step_number

    def clear_highlight(self) -> None:
        """Remove highlighting from all rows."""
        if self._current_step is not None:
            item_id = self._step_to_item.get(self._current_step)
            if item_id and self._tree.exists(item_id):
                self._tree.item(item_id, tags=())
        self._current_step = None

    def get_selected_step_number(self) -> int | None:
        """
        Get the step number of the currently user-selected row.

        Returns:
            1-based step number, or None if no row is selected
        """
        selection = self._tree.selection()
        if not selection:
            return None

        item_id = selection[0]
        for step_number, stored_item_id in self._step_to_item.items():
            if stored_item_id == item_id:
                return step_number

        return None

    def register_selection_callback(
        self, callback: Callable[[int | None], None]
    ) -> None:
        """
        Register callback for row selection changes.

        Args:
            callback: Called with step_number (int) or None when selection changes
        """

        def on_select(event) -> None:  # type: ignore[no-untyped-def]
            step_number = self.get_selected_step_number()
            callback(step_number)

        self._tree.bind("<<TreeviewSelect>>", on_select)

    def clear(self) -> None:
        """Remove all rows from the table."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._step_to_item.clear()
        self._current_step = None
