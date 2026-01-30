"""Resource Manager dialog for scanning, identifying, and connecting to VISA resources."""

import tkinter as tk
from tkinter import ttk
from typing import Callable


class ResourceManagerDialog:
    """
    Modal dialog for scanning, identifying, and connecting to VISA resources.

    Provides three operations:
    - Scan: List available VISA resources without opening them
    - Identify: Open each resource, query *IDN?, display model, close
    - Connect: Connect to selected resource with specified instrument type
    """

    def __init__(self, parent: tk.Tk):
        """
        Initialize dialog window.

        Args:
            parent: Parent Tkinter window
        """
        self._parent = parent
        self._result: tuple[str, str] | None = None

        # Callbacks set by presenter
        self._on_scan: Callable[[], None] | None = None
        self._on_identify: Callable[[], None] | None = None

        # Resource data: {resource_address: identification_string or None}
        self._resource_data: dict[str, str | None] = {}

        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the dialog window and widgets."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Resource Manager")
        self._dialog.geometry("500x400")
        self._dialog.resizable(True, True)
        self._dialog.minsize(400, 300)

        # Make dialog modal
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Handle window close button
        self._dialog.protocol("WM_DELETE_WINDOW", self._handle_cancel)

        # Configure grid
        self._dialog.columnconfigure(0, weight=1)
        self._dialog.rowconfigure(1, weight=1)

        # Create widgets
        self._create_header()
        self._create_resource_list()
        self._create_instrument_type_selector()
        self._create_buttons()
        self._create_status_bar()

        # Center dialog on parent
        self._center_on_parent()

    def _create_header(self) -> None:
        """Create header label."""
        header = ttk.Label(
            self._dialog,
            text="Available VISA Resources:",
            font=("TkDefaultFont", 10, "bold"),
        )
        header.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

    def _create_resource_list(self) -> None:
        """Create the treeview for displaying resources."""
        # Frame for treeview and scrollbar
        list_frame = ttk.Frame(self._dialog)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Treeview with two columns
        self._tree = ttk.Treeview(
            list_frame,
            columns=("resource", "identification"),
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("resource", text="Resource Address")
        self._tree.heading("identification", text="Identification")
        self._tree.column("resource", width=200, minwidth=150)
        self._tree.column("identification", width=250, minwidth=150)

        # Scrollbars
        y_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._tree.yview)
        x_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        self._tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # Bind selection event to update Connect button state
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

    def _create_instrument_type_selector(self) -> None:
        """Create instrument type dropdown."""
        type_frame = ttk.Frame(self._dialog)
        type_frame.grid(row=2, column=0, sticky="w", padx=10, pady=5)

        ttk.Label(type_frame, text="Instrument Type:").pack(side=tk.LEFT, padx=(0, 5))

        self._type_var = tk.StringVar(value="Power Supply")
        self._type_combo = ttk.Combobox(
            type_frame,
            textvariable=self._type_var,
            values=["Power Supply", "Signal Generator"],
            state="readonly",
            width=20,
        )
        self._type_combo.pack(side=tk.LEFT)

    def _create_buttons(self) -> None:
        """Create action buttons."""
        btn_frame = ttk.Frame(self._dialog)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        self._scan_btn = ttk.Button(btn_frame, text="Scan", command=self._handle_scan)
        self._scan_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._identify_btn = ttk.Button(
            btn_frame, text="Identify", command=self._handle_identify, state=tk.DISABLED
        )
        self._identify_btn.pack(side=tk.LEFT, padx=5)

        self._connect_btn = ttk.Button(
            btn_frame, text="Connect", command=self._handle_connect, state=tk.DISABLED
        )
        self._connect_btn.pack(side=tk.LEFT, padx=5)

        self._cancel_btn = ttk.Button(
            btn_frame, text="Cancel", command=self._handle_cancel
        )
        self._cancel_btn.pack(side=tk.RIGHT)

    def _create_status_bar(self) -> None:
        """Create status bar at bottom."""
        self._status_label = ttk.Label(
            self._dialog,
            text="Click Scan to discover available resources",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        self._status_label.grid(row=4, column=0, sticky="ew", padx=5, pady=(0, 5))

    def _center_on_parent(self) -> None:
        """Center dialog on parent window."""
        self._dialog.update_idletasks()
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        parent_w = self._parent.winfo_width()
        parent_h = self._parent.winfo_height()
        dialog_w = self._dialog.winfo_width()
        dialog_h = self._dialog.winfo_height()

        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self._dialog.geometry(f"+{x}+{y}")

    # Button handlers

    def _handle_scan(self) -> None:
        """Handle Scan button click."""
        if self._on_scan:
            self._on_scan()

    def _handle_identify(self) -> None:
        """Handle Identify button click."""
        if self._on_identify:
            self._on_identify()

    def _handle_connect(self) -> None:
        """Handle Connect button click."""
        selected = self.get_selected_resource()
        if selected:
            instrument_type = self.get_selected_instrument_type()
            self._result = (selected, instrument_type)
            self._dialog.destroy()

    def _handle_cancel(self) -> None:
        """Handle Cancel button or window close."""
        self._result = None
        self._dialog.destroy()

    def _on_selection_changed(self, event) -> None:
        """Handle treeview selection change."""
        selected = self.get_selected_resource()
        self._connect_btn.config(state=tk.NORMAL if selected else tk.DISABLED)

    # Callback setters

    def set_on_scan(self, callback: Callable[[], None]) -> None:
        """Set callback for Scan button."""
        self._on_scan = callback

    def set_on_identify(self, callback: Callable[[], None]) -> None:
        """Set callback for Identify button."""
        self._on_identify = callback

    # Public methods for presenter to update dialog state

    def show(self) -> tuple[str, str] | None:
        """
        Show dialog modally and wait for result.

        Returns:
            Tuple of (resource_address, instrument_type) if connected,
            None if cancelled
        """
        self._dialog.wait_window()
        return self._result

    def set_resources(self, resources: list[str]) -> None:
        """
        Populate resource list.

        Args:
            resources: List of VISA resource address strings
        """
        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._resource_data.clear()

        # Add new items
        for resource in resources:
            self._tree.insert("", tk.END, values=(resource, "(Not identified)"))
            self._resource_data[resource] = None

        # Update button states
        has_resources = len(resources) > 0
        self._identify_btn.config(state=tk.NORMAL if has_resources else tk.DISABLED)
        self._connect_btn.config(state=tk.DISABLED)  # Need selection

    def set_resource_identification(self, resource: str, idn: str | None) -> None:
        """
        Update identification for a resource.

        Args:
            resource: VISA resource address
            idn: Identification string from *IDN? query, or None if failed
        """
        self._resource_data[resource] = idn

        # Find and update the treeview item
        for item in self._tree.get_children():
            values = self._tree.item(item, "values")
            if values and values[0] == resource:
                display_idn = idn if idn else "(Failed to identify)"
                self._tree.item(item, values=(resource, display_idn))
                break

    def set_status(self, message: str) -> None:
        """Update status bar message."""
        self._status_label.config(text=message)

    def set_buttons_enabled(
        self, scan: bool, identify: bool, connect: bool
    ) -> None:
        """
        Enable/disable buttons.

        Args:
            scan: Enable Scan button
            identify: Enable Identify button
            connect: Enable Connect button (only if also has selection)
        """
        self._scan_btn.config(state=tk.NORMAL if scan else tk.DISABLED)
        self._identify_btn.config(state=tk.NORMAL if identify else tk.DISABLED)

        # Connect button also requires selection
        has_selection = self.get_selected_resource() is not None
        self._connect_btn.config(
            state=tk.NORMAL if connect and has_selection else tk.DISABLED
        )

    def get_selected_resource(self) -> str | None:
        """Get currently selected resource address."""
        selection = self._tree.selection()
        if selection:
            item = selection[0]
            values = self._tree.item(item, "values")
            if values:
                return values[0]
        return None

    def get_selected_instrument_type(self) -> str:
        """Get selected instrument type as internal string."""
        display_type = self._type_var.get()
        if display_type == "Signal Generator":
            return "signal_generator"
        return "power_supply"

    def get_resources(self) -> list[str]:
        """Get list of all resource addresses."""
        return list(self._resource_data.keys())

    def close(self) -> None:
        """Close the dialog."""
        self._dialog.destroy()
