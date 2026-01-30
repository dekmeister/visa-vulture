"""Main application window."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .log_panel import LogPanel
from .plot_panel import PowerSupplyPlotPanel, SignalGeneratorPlotPanel
from .test_points_table import TestPointsTable, InstrumentType


class MainWindow:
    """
    Main application window.

    Assembles all GUI panels and exposes callbacks for presenter.
    Does not contain business logic.
    """

    def __init__(
        self,
        root: tk.Tk,
        title: str = "VISA Vulture",
        width: int = 1200,
        height: int = 800,
    ):
        """
        Initialize main window.

        Args:
            root: Tkinter root window
            title: Window title
            width: Window width
            height: Window height
        """
        self._root = root
        self._root.title(title)
        self._root.geometry(f"{width}x{height}")

        # Callbacks set by presenter
        self._on_connect: Callable[[], None] | None = None
        self._on_disconnect: Callable[[], None] | None = None
        self._on_load_test_plan: Callable[[str], None] | None = None
        self._on_run: Callable[[], None] | None = None
        self._on_stop: Callable[[], None] | None = None
        self._on_pause: Callable[[], None] | None = None
        self._on_start_from: Callable[[], None] | None = None

        # Tooltip state
        self._tooltip: tk.Toplevel | None = None
        self._tooltip_text: str | None = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create all GUI widgets."""
        # Configure grid
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        # Top control panel
        self._create_control_panel()

        # Main content with paned windows
        self._create_content_area()

        # Status bar
        self._create_status_bar()

    def _create_control_panel(self) -> None:
        """Create top control panel."""
        panel = ttk.Frame(self._root, padding=5)
        panel.grid(row=0, column=0, sticky="ew")

        # Connection section
        conn_frame = ttk.LabelFrame(panel, text="Connection", padding=5)
        conn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self._connect_btn = ttk.Button(
            conn_frame, text="Connect", command=self._handle_connect
        )
        self._connect_btn.pack(side=tk.LEFT, padx=2)

        self._disconnect_btn = ttk.Button(
            conn_frame,
            text="Disconnect",
            command=self._handle_disconnect,
            state=tk.DISABLED,
        )
        self._disconnect_btn.pack(side=tk.LEFT, padx=2)

        # Connection indicator
        self._conn_indicator = ttk.Label(conn_frame, text="\u25cf", foreground="gray")
        self._conn_indicator.pack(side=tk.LEFT, padx=5)

        # Test plan section
        plan_frame = ttk.LabelFrame(panel, text="Test Plan", padding=5)
        plan_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self._load_btn = ttk.Button(
            plan_frame, text="Load...", command=self._handle_load_test_plan
        )
        self._load_btn.pack(side=tk.LEFT, padx=2)

        self._plan_label = ttk.Label(plan_frame, text="No plan loaded", width=30)
        self._plan_label.pack(side=tk.LEFT, padx=5)

        # Run section
        run_frame = ttk.LabelFrame(panel, text="Execution", padding=5)
        run_frame.pack(side=tk.LEFT, fill=tk.Y)

        self._run_btn = ttk.Button(
            run_frame, text="Run", command=self._handle_run, state=tk.DISABLED
        )
        self._run_btn.pack(side=tk.LEFT, padx=2)

        self._stop_btn = ttk.Button(
            run_frame, text="Stop", command=self._handle_stop, state=tk.DISABLED
        )
        self._stop_btn.pack(side=tk.LEFT, padx=2)

        self._pause_btn = ttk.Button(
            run_frame, text="Pause", command=self._handle_pause, state=tk.DISABLED
        )
        self._pause_btn.pack(side=tk.LEFT, padx=2)

        self._start_from_btn = ttk.Button(
            run_frame,
            text="Start from...",
            command=self._handle_start_from,
            state=tk.DISABLED,
        )
        self._start_from_btn.pack(side=tk.LEFT, padx=2)

        # State and runtime display (vertical layout)
        status_frame = ttk.Frame(panel)
        status_frame.pack(side=tk.RIGHT, padx=10)

        # Instrument identification display (top row)
        instrument_frame = ttk.Frame(status_frame)
        instrument_frame.pack(side=tk.TOP, anchor=tk.E)
        self._instrument_label = ttk.Label(
            instrument_frame, text="", font=("TkDefaultFont", 9), foreground="gray"
        )
        self._instrument_label.pack(side=tk.LEFT)
        self._instrument_label.bind("<Enter>", self._on_instrument_enter)
        self._instrument_label.bind("<Leave>", self._on_instrument_leave)

        # State display (second row)
        state_frame = ttk.Frame(status_frame)
        state_frame.pack(side=tk.TOP, anchor=tk.E)
        ttk.Label(state_frame, text="State:").pack(side=tk.LEFT)
        self._state_label = ttk.Label(
            state_frame, text="UNKNOWN", font=("TkDefaultFont", 10, "bold")
        )
        self._state_label.pack(side=tk.LEFT, padx=5)

        # Runtime and remaining time display (bottom row)
        runtime_frame = ttk.Frame(status_frame)
        runtime_frame.pack(side=tk.TOP, anchor=tk.E, pady=(2, 0))
        ttk.Label(runtime_frame, text="Runtime:").pack(side=tk.LEFT)
        self._runtime_label = ttk.Label(
            runtime_frame, text="--:--", font=("TkDefaultFont", 10, "bold")
        )
        self._runtime_label.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(runtime_frame, text="Remaining:").pack(side=tk.LEFT)
        self._remaining_label = ttk.Label(
            runtime_frame, text="--:--", font=("TkDefaultFont", 10, "bold")
        )
        self._remaining_label.pack(side=tk.LEFT, padx=5)

    def _create_content_area(self) -> None:
        """Create main content area with plot, table, and log panels."""
        # Vertical paned window
        paned = ttk.PanedWindow(self._root, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Plot container with notebook for switching between plot types
        self._plot_notebook = ttk.Notebook(paned)
        paned.add(self._plot_notebook, weight=2)

        # Power supply tab: horizontal paned window with plot and table
        self._ps_container = ttk.PanedWindow(self._plot_notebook, orient=tk.HORIZONTAL)
        self._plot_notebook.add(self._ps_container, text="Power Supply")

        self._power_supply_plot_panel = PowerSupplyPlotPanel(self._ps_container)
        self._ps_container.add(self._power_supply_plot_panel, weight=3)

        self._ps_table = TestPointsTable(self._ps_container, InstrumentType.POWER_SUPPLY)
        self._ps_container.add(self._ps_table, weight=1)

        # Signal generator tab: horizontal paned window with plot and table
        self._sg_container = ttk.PanedWindow(self._plot_notebook, orient=tk.HORIZONTAL)
        self._plot_notebook.add(self._sg_container, text="Signal Generator")

        self._signal_gen_plot_panel = SignalGeneratorPlotPanel(self._sg_container)
        self._sg_container.add(self._signal_gen_plot_panel, weight=3)

        self._sg_table = TestPointsTable(self._sg_container, InstrumentType.SIGNAL_GENERATOR)
        self._sg_container.add(self._sg_table, weight=1)

        # Track which tabs are currently visible
        self._ps_tab_visible = True
        self._sg_tab_visible = True

        # Log panel (bottom)
        self._log_panel = LogPanel(paned)
        paned.add(self._log_panel, weight=1)

    def _create_status_bar(self) -> None:
        """Create bottom status bar."""
        self._status_bar = ttk.Label(
            self._root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        self._status_bar.grid(row=2, column=0, sticky="ew")

    # Callback handlers

    def _handle_connect(self) -> None:
        """Handle connect button click."""
        if self._on_connect:
            self._on_connect()

    def _handle_disconnect(self) -> None:
        """Handle disconnect button click."""
        if self._on_disconnect:
            self._on_disconnect()

    def _handle_load_test_plan(self) -> None:
        """Handle load test plan button click."""
        file_path = filedialog.askopenfilename(
            title="Select Test Plan",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if file_path and self._on_load_test_plan:
            self._on_load_test_plan(file_path)

    def _handle_run(self) -> None:
        """Handle run button click."""
        if self._on_run:
            self._on_run()

    def _handle_stop(self) -> None:
        """Handle stop button click."""
        if self._on_stop:
            self._on_stop()

    def _handle_pause(self) -> None:
        """Handle pause button click."""
        if self._on_pause:
            self._on_pause()

    def _handle_start_from(self) -> None:
        """Handle start from button click."""
        if self._on_start_from:
            self._on_start_from()

    # Callback setters

    def set_on_connect(self, callback: Callable[[], None]) -> None:
        """Set callback for connect button."""
        self._on_connect = callback

    def set_on_disconnect(self, callback: Callable[[], None]) -> None:
        """Set callback for disconnect button."""
        self._on_disconnect = callback

    def set_on_load_test_plan(self, callback: Callable[[str], None]) -> None:
        """Set callback for load test plan button."""
        self._on_load_test_plan = callback

    def set_on_run(self, callback: Callable[[], None]) -> None:
        """Set callback for run button."""
        self._on_run = callback

    def set_on_stop(self, callback: Callable[[], None]) -> None:
        """Set callback for stop button."""
        self._on_stop = callback

    def set_on_pause(self, callback: Callable[[], None]) -> None:
        """Set callback for pause button."""
        self._on_pause = callback

    def set_on_start_from(self, callback: Callable[[], None]) -> None:
        """Set callback for start from button."""
        self._on_start_from = callback

    # View update methods

    def set_state_display(self, state: str) -> None:
        """
        Update state display.

        Args:
            state: State name to display
        """
        self._state_label.config(text=state)

        # Color coding
        colors = {
            "UNKNOWN": "gray",
            "IDLE": "green",
            "RUNNING": "blue",
            "PAUSED": "orange",
            "ERROR": "red",
        }
        self._state_label.config(foreground=colors.get(state, "black"))

    def set_runtime_display(self, elapsed_seconds: int | None) -> None:
        """
        Update runtime display.

        Args:
            elapsed_seconds: Elapsed time in seconds, or None to show --:--
        """
        if elapsed_seconds is None:
            self._runtime_label.config(text="--:--")
        else:
            minutes = elapsed_seconds // 60
            seconds = elapsed_seconds % 60
            self._runtime_label.config(text=f"{minutes:02d}:{seconds:02d}")

    def set_remaining_time_display(self, remaining_seconds: float | None) -> None:
        """
        Update remaining time display.

        Args:
            remaining_seconds: Remaining time in seconds, or None to show --:--
        """
        if remaining_seconds is None:
            self._remaining_label.config(text="--:--")
        else:
            remaining_int = max(0, int(remaining_seconds))
            minutes = remaining_int // 60
            seconds = remaining_int % 60
            self._remaining_label.config(text=f"{minutes:02d}:{seconds:02d}")

    def set_connection_status(self, connected: bool) -> None:
        """
        Update connection indicator.

        Args:
            connected: True if connected
        """
        color = "green" if connected else "gray"
        self._conn_indicator.config(foreground=color)

    def set_buttons_for_state(self, state: str) -> None:
        """
        Enable/disable buttons based on state.

        Args:
            state: Current state name
        """
        if state == "UNKNOWN":
            self._connect_btn.config(state=tk.NORMAL)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._load_btn.config(state=tk.NORMAL)
            self._run_btn.config(state=tk.DISABLED)
            self._stop_btn.config(state=tk.DISABLED)
            self._pause_btn.config(state=tk.DISABLED)
            self._start_from_btn.config(state=tk.DISABLED)
            self.set_run_button_text("Run")
            self.set_start_from_button_text("Start from...")
        elif state == "IDLE":
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._load_btn.config(state=tk.NORMAL)
            self._run_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.DISABLED)
            self._pause_btn.config(state=tk.DISABLED)
            self._start_from_btn.config(state=tk.DISABLED)  # Presenter enables if selected
            self.set_run_button_text("Run")
            self.set_start_from_button_text("Start from...")
        elif state == "RUNNING":
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._load_btn.config(state=tk.DISABLED)
            self._run_btn.config(state=tk.DISABLED)
            self._stop_btn.config(state=tk.NORMAL)
            self._pause_btn.config(state=tk.NORMAL)
            self._start_from_btn.config(state=tk.DISABLED)
            self.set_run_button_text("Run")
        elif state == "PAUSED":
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._load_btn.config(state=tk.DISABLED)
            self._run_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.NORMAL)
            self._pause_btn.config(state=tk.DISABLED)
            self._start_from_btn.config(state=tk.DISABLED)  # Presenter enables if selected
            self.set_run_button_text("Resume")
            self.set_start_from_button_text("Resume from...")
        elif state == "ERROR":
            self._connect_btn.config(state=tk.NORMAL)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._load_btn.config(state=tk.NORMAL)
            self._run_btn.config(state=tk.DISABLED)
            self._stop_btn.config(state=tk.DISABLED)
            self._pause_btn.config(state=tk.DISABLED)
            self._start_from_btn.config(state=tk.DISABLED)
            self.set_run_button_text("Run")
            self.set_start_from_button_text("Start from...")

    def set_run_button_text(self, text: str) -> None:
        """
        Update Run button text.

        Args:
            text: Button text (e.g., 'Run' or 'Resume')
        """
        self._run_btn.config(text=text)

    def set_test_plan_name(self, name: str | None) -> None:
        """
        Update test plan display.

        Args:
            name: Test plan name or None
        """
        if name:
            self._plan_label.config(text=name)
        else:
            self._plan_label.config(text="No plan loaded")

    def set_status(self, message: str) -> None:
        """
        Update status bar message.

        Args:
            message: Status message
        """
        self._status_bar.config(text=message)

    def set_instrument_display(self, model: str | None, tooltip: str | None) -> None:
        """
        Update instrument identification display.

        Args:
            model: Model name to display, or None to clear
            tooltip: Full identification text for tooltip, or None
        """
        if model:
            self._instrument_label.config(text=model, foreground="black")
            self._tooltip_text = tooltip
        else:
            self._instrument_label.config(text="", foreground="gray")
            self._tooltip_text = None

    def _on_instrument_enter(self, event) -> None:
        """Handle mouse entering instrument label."""
        if self._tooltip_text:
            self._show_tooltip(event, self._tooltip_text)

    def _on_instrument_leave(self, event) -> None:
        """Handle mouse leaving instrument label."""
        self._hide_tooltip()

    def _show_tooltip(self, event, text: str) -> None:
        """
        Show tooltip near widget.

        Args:
            event: Mouse event with position info
            text: Tooltip text to display
        """
        if self._tooltip:
            self._hide_tooltip()

        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty() + event.widget.winfo_height() + 5

        self._tooltip = tk.Toplevel(self._root)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self._tooltip,
            text=text,
            background="#FFFFDD",
            relief=tk.SOLID,
            borderwidth=1,
            padding=(5, 3),
            font=("TkDefaultFont", 9),
        )
        label.pack()

    def _hide_tooltip(self) -> None:
        """Hide tooltip."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def show_error(self, title: str, message: str) -> None:
        """
        Show error dialog.

        Args:
            title: Dialog title
            message: Error message
        """
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str) -> None:
        """
        Show info dialog.

        Args:
            title: Dialog title
            message: Info message
        """
        messagebox.showinfo(title, message)

    def show_confirmation(self, title: str, message: str) -> bool:
        """
        Show yes/no confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message

        Returns:
            True if user confirmed, False otherwise
        """
        return messagebox.askyesno(title, message)

    def get_active_table_selected_step(self) -> int | None:
        """
        Get the selected step number from the currently active table tab.

        Returns:
            1-based step number, or None if no selection
        """
        tab_index = self.get_selected_tab_index()
        if tab_index == 0:
            return self._ps_table.get_selected_step_number()
        else:
            return self._sg_table.get_selected_step_number()

    def set_start_from_button_text(self, text: str) -> None:
        """Update Start from button text."""
        self._start_from_btn.config(text=text)

    def set_start_from_enabled(self, enabled: bool) -> None:
        """Enable or disable the Start from button."""
        self._start_from_btn.config(state=tk.NORMAL if enabled else tk.DISABLED)

    # Component access

    @property
    def log_panel(self) -> LogPanel:
        """Get log panel widget."""
        return self._log_panel

    @property
    def power_supply_plot_panel(self) -> PowerSupplyPlotPanel:
        """Get power supply plot panel widget."""
        return self._power_supply_plot_panel

    @property
    def signal_gen_plot_panel(self) -> SignalGeneratorPlotPanel:
        """Get signal generator plot panel widget."""
        return self._signal_gen_plot_panel

    @property
    def ps_table(self) -> TestPointsTable:
        """Get power supply test points table."""
        return self._ps_table

    @property
    def sg_table(self) -> TestPointsTable:
        """Get signal generator test points table."""
        return self._sg_table

    @property
    def plot_notebook(self) -> ttk.Notebook:
        """Get plot notebook widget for tab change binding."""
        return self._plot_notebook

    def get_selected_tab_index(self) -> int:
        """Get the index of the currently selected plot tab."""
        return int(self._plot_notebook.index(self._plot_notebook.select()))

    def show_power_supply_plot(self) -> None:
        """Switch to power supply plot tab."""
        if self._ps_tab_visible:
            self._plot_notebook.select(self._ps_container)

    def show_signal_generator_plot(self) -> None:
        """Switch to signal generator plot tab."""
        if self._sg_tab_visible:
            self._plot_notebook.select(self._sg_container)

    def show_power_supply_tab_only(self) -> None:
        """Show only power supply tab, hide signal generator tab."""
        # Ensure power supply tab is visible
        if not self._ps_tab_visible:
            self._plot_notebook.add(self._ps_container, text="Power Supply")
            self._ps_tab_visible = True

        # Hide signal generator tab if visible
        if self._sg_tab_visible:
            self._plot_notebook.hide(self._sg_container)
            self._sg_tab_visible = False

        # Select power supply tab
        self._plot_notebook.select(self._ps_container)

    def show_signal_generator_tab_only(self) -> None:
        """Show only signal generator tab, hide power supply tab."""
        # Ensure signal generator tab is visible
        if not self._sg_tab_visible:
            self._plot_notebook.add(self._sg_container, text="Signal Generator")
            self._sg_tab_visible = True

        # Hide power supply tab if visible
        if self._ps_tab_visible:
            self._plot_notebook.hide(self._ps_container)
            self._ps_tab_visible = False

        # Select signal generator tab
        self._plot_notebook.select(self._sg_container)

    def show_all_tabs(self) -> None:
        """Show both tabs (for disconnected state)."""
        # Re-add power supply tab if hidden
        if not self._ps_tab_visible:
            self._plot_notebook.add(self._ps_container, text="Power Supply")
            self._ps_tab_visible = True

        # Re-add signal generator tab if hidden
        if not self._sg_tab_visible:
            self._plot_notebook.add(self._sg_container, text="Signal Generator")
            self._sg_tab_visible = True

        # Select power supply tab by default
        self._plot_notebook.select(self._ps_container)

    def schedule(self, delay_ms: int, callback: Callable[[], None]) -> str:
        """
        Schedule a callback on the main thread.

        Args:
            delay_ms: Delay in milliseconds
            callback: Function to call

        Returns:
            Timer ID for cancellation
        """
        return self._root.after(delay_ms, callback)

    def cancel_schedule(self, timer_id: str) -> None:
        """
        Cancel a scheduled callback.

        Args:
            timer_id: Timer ID from schedule()
        """
        self._root.after_cancel(timer_id)
