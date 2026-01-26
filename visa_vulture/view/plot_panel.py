"""Plot panel widget for real-time data visualization."""

import tkinter as tk
from tkinter import ttk
from typing import Sequence

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


class PlotPanel(ttk.Frame):
    """
    Panel for displaying real-time voltage and current plots.

    Embeds matplotlib figure with dual y-axis for voltage and current.
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize plot panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Data storage
        self._times: list[float] = []
        self._voltages: list[float] = []
        self._currents: list[float] = []

        # Position indicator
        self._position_line: Line2D | None = None

        # Y-axis scale state: 'linear' or 'log'
        self._voltage_scale: str = "linear"
        self._current_scale: str = "linear"

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create matplotlib figure and canvas."""
        # Create figure with constrained layout
        self._figure = Figure(figsize=(8, 4), dpi=100)
        self._figure.tight_layout()

        # Primary axis for voltage
        self._ax_voltage = self._figure.add_subplot(111)
        self._ax_voltage.set_xlabel("Time (s)")
        self._ax_voltage.set_ylabel("Voltage (V)", color="blue")
        self._ax_voltage.tick_params(axis="y", labelcolor="blue")
        self._ax_voltage.grid(True, alpha=0.3)

        # Secondary axis for current
        self._ax_current = self._ax_voltage.twinx()
        self._ax_current.set_ylabel("Current (A)", color="red")
        self._ax_current.tick_params(axis="y", labelcolor="red")

        # Create plot lines (steps-post holds value constant until next point)
        (self._voltage_line,) = self._ax_voltage.plot(
            [], [], "b-", label="Voltage", linewidth=2, drawstyle="steps-post"
        )
        (self._current_line,) = self._ax_current.plot(
            [], [], "r-", label="Current", linewidth=2, drawstyle="steps-post"
        )

        # Legend
        lines = [self._voltage_line, self._current_line]
        labels = [str(line.get_label()) for line in lines]
        self._ax_voltage.legend(lines, labels, loc="upper left")

        # Embed in Tkinter
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X)
        self._toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        self._toolbar.update()

        # Right-click context menu for scale selection
        self._canvas.get_tk_widget().bind("<Button-3>", self._show_scale_menu)

    def add_point(self, time: float, voltage: float, current: float) -> None:
        """
        Add a data point to the plot.

        Args:
            time: Time in seconds
            voltage: Voltage reading
            current: Current reading
        """
        self._times.append(time)
        self._voltages.append(voltage)
        self._currents.append(current)

        self._update_plot()

    def set_data(
        self,
        times: Sequence[float],
        voltages: Sequence[float],
        currents: Sequence[float],
    ) -> None:
        """
        Replace all plot data.

        Args:
            times: Time values
            voltages: Voltage values
            currents: Current values
        """
        self._times = list(times)
        self._voltages = list(voltages)
        self._currents = list(currents)

        self._update_plot()

    def set_current_position(self, time: float) -> None:
        """
        Set the current test position indicator.

        Args:
            time: Current time position in seconds
        """
        # Remove existing position line
        if self._position_line is not None:
            self._position_line.remove()
            self._position_line = None

        # Add new position line
        if self._times:
            self._position_line = self._ax_voltage.axvline(
                x=time,
                color="red",
                linestyle="--",
                linewidth=2,
                alpha=0.7,
                label="_nolegend_",
            )

        self._canvas.draw_idle()

    def clear_position(self) -> None:
        """Clear the current position indicator."""
        if self._position_line is not None:
            self._position_line.remove()
            self._position_line = None
            self._canvas.draw_idle()

    def _show_scale_menu(self, event: "tk.Event[tk.Widget]") -> None:
        """Show right-click context menu for Y-axis scale selection."""
        menu = tk.Menu(self, tearoff=0)

        voltage_label = (
            "Voltage Y-Axis: Switch to Log"
            if self._voltage_scale == "linear"
            else "Voltage Y-Axis: Switch to Linear"
        )
        menu.add_command(label=voltage_label, command=self._toggle_voltage_scale)

        current_label = (
            "Current Y-Axis: Switch to Log"
            if self._current_scale == "linear"
            else "Current Y-Axis: Switch to Linear"
        )
        menu.add_command(label=current_label, command=self._toggle_current_scale)

        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_voltage_scale(self) -> None:
        """Toggle voltage Y-axis between linear and log scale."""
        self._voltage_scale = "log" if self._voltage_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _toggle_current_scale(self) -> None:
        """Toggle current Y-axis between linear and log scale."""
        self._current_scale = "log" if self._current_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _apply_scales(self) -> None:
        """Apply current scale settings to axes and update labels."""
        self._ax_voltage.set_yscale(self._voltage_scale)
        self._ax_current.set_yscale(self._current_scale)

        voltage_suffix = " (log)" if self._voltage_scale == "log" else ""
        current_suffix = " (log)" if self._current_scale == "log" else ""
        self._ax_voltage.set_ylabel(f"Voltage (V){voltage_suffix}", color="blue")
        self._ax_current.set_ylabel(f"Current (A){current_suffix}", color="red")

    def _set_ylim_for_scale(
        self,
        ax: Axes,
        values: list[float],
        scale: str,
        lower_bound_zero: bool = True,
    ) -> None:
        """
        Set Y-axis limits appropriate for the current scale mode.

        Args:
            ax: The matplotlib axis to set limits on
            values: Data values for computing limits
            scale: 'linear' or 'log'
            lower_bound_zero: Whether the lower bound should be 0 in linear mode
        """
        if not values:
            return

        if scale == "log":
            positive_values = [v for v in values if v > 0]
            if positive_values:
                v_min = min(positive_values)
                v_max = max(positive_values)
                ax.set_ylim(v_min / 2, v_max * 2)
            else:
                ax.set_ylim(0.1, 10)
        else:
            v_min = min(values)
            v_max = max(values)
            if lower_bound_zero:
                ax.set_ylim(0, v_max * 1.1 or 1)
            else:
                margin = (v_max - v_min) * 0.1 or 1
                ax.set_ylim(v_min - margin, v_max + margin)

    def load_test_plan_preview(
        self,
        times: Sequence[float],
        voltages: Sequence[float],
        currents: Sequence[float],
    ) -> None:
        """
        Load test plan data as a preview (shows full plan trajectory).

        Args:
            times: Time values
            voltages: Voltage values
            currents: Current values
        """
        self.set_data(times, voltages, currents)
        self.clear_position()

    def _update_plot(self) -> None:
        """Update plot with current data."""
        # Update line data
        self._voltage_line.set_data(self._times, self._voltages)
        self._current_line.set_data(self._times, self._currents)

        # Adjust axis limits
        if self._times:
            self._ax_voltage.set_xlim(0, max(self._times) * 1.05 or 1)

            if self._voltages:
                self._set_ylim_for_scale(
                    self._ax_voltage,
                    self._voltages,
                    self._voltage_scale,
                    lower_bound_zero=True,
                )

            if self._currents:
                self._set_ylim_for_scale(
                    self._ax_current,
                    self._currents,
                    self._current_scale,
                    lower_bound_zero=True,
                )

        # Redraw
        self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear all plot data and position indicator."""
        self._times.clear()
        self._voltages.clear()
        self._currents.clear()

        self._voltage_line.set_data([], [])
        self._current_line.set_data([], [])

        # Clear position line
        if self._position_line is not None:
            self._position_line.remove()
            self._position_line = None

        # Reset scales to defaults
        self._voltage_scale = "linear"
        self._current_scale = "linear"
        self._apply_scales()

        self._ax_voltage.set_xlim(0, 1)
        self._ax_voltage.set_ylim(0, 1)
        self._ax_current.set_ylim(0, 1)

        self._canvas.draw_idle()

    def set_title(self, title: str) -> None:
        """
        Set plot title.

        Args:
            title: Title text
        """
        self._ax_voltage.set_title(title)
        self._canvas.draw_idle()
