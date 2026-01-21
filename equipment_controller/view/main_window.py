"""Main application window."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from .log_panel import LogPanel
from .plot_panel import PlotPanel
from .signal_generator_plot_panel import SignalGeneratorPlotPanel


class MainWindow:
    """
    Main application window.

    Assembles all GUI panels and exposes callbacks for presenter.
    Does not contain business logic.
    """

    def __init__(self, root: tk.Tk, title: str = "Equipment Controller", width: int = 1200, height: int = 800):
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
            conn_frame, text="Disconnect", command=self._handle_disconnect, state=tk.DISABLED
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

        # Progress bar
        self._progress = ttk.Progressbar(run_frame, length=150, mode="determinate")
        self._progress.pack(side=tk.LEFT, padx=5)

        # State display
        state_frame = ttk.Frame(panel)
        state_frame.pack(side=tk.RIGHT, padx=10)

        ttk.Label(state_frame, text="State:").pack(side=tk.LEFT)
        self._state_label = ttk.Label(state_frame, text="UNKNOWN", font=("TkDefaultFont", 10, "bold"))
        self._state_label.pack(side=tk.LEFT, padx=5)

    def _create_content_area(self) -> None:
        """Create main content area with plot and log panels."""
        # Vertical paned window
        paned = ttk.PanedWindow(self._root, orient=tk.VERTICAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Plot container with notebook for switching between plot types
        self._plot_notebook = ttk.Notebook(paned)
        paned.add(self._plot_notebook, weight=2)

        # Power supply plot panel
        self._plot_panel = PlotPanel(self._plot_notebook)
        self._plot_notebook.add(self._plot_panel, text="Power Supply")

        # Signal generator plot panel
        self._signal_gen_plot_panel = SignalGeneratorPlotPanel(self._plot_notebook)
        self._plot_notebook.add(self._signal_gen_plot_panel, text="Signal Generator")

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
            "ERROR": "red",
        }
        self._state_label.config(foreground=colors.get(state, "black"))

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
        elif state == "IDLE":
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._load_btn.config(state=tk.NORMAL)
            self._run_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.DISABLED)
        elif state == "RUNNING":
            self._connect_btn.config(state=tk.DISABLED)
            self._disconnect_btn.config(state=tk.DISABLED)
            self._load_btn.config(state=tk.DISABLED)
            self._run_btn.config(state=tk.DISABLED)
            self._stop_btn.config(state=tk.NORMAL)
        elif state == "ERROR":
            self._connect_btn.config(state=tk.NORMAL)
            self._disconnect_btn.config(state=tk.NORMAL)
            self._load_btn.config(state=tk.NORMAL)
            self._run_btn.config(state=tk.DISABLED)
            self._stop_btn.config(state=tk.DISABLED)

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

    def set_progress(self, current: int, total: int) -> None:
        """
        Update progress bar.

        Args:
            current: Current step
            total: Total steps
        """
        if total > 0:
            self._progress["maximum"] = total
            self._progress["value"] = current
        else:
            self._progress["value"] = 0

    def set_status(self, message: str) -> None:
        """
        Update status bar message.

        Args:
            message: Status message
        """
        self._status_bar.config(text=message)

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

    # Component access

    @property
    def log_panel(self) -> LogPanel:
        """Get log panel widget."""
        return self._log_panel

    @property
    def plot_panel(self) -> PlotPanel:
        """Get power supply plot panel widget."""
        return self._plot_panel

    @property
    def signal_gen_plot_panel(self) -> SignalGeneratorPlotPanel:
        """Get signal generator plot panel widget."""
        return self._signal_gen_plot_panel

    def show_power_supply_plot(self) -> None:
        """Switch to power supply plot tab."""
        self._plot_notebook.select(0)

    def show_signal_generator_plot(self) -> None:
        """Switch to signal generator plot tab."""
        self._plot_notebook.select(1)

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
