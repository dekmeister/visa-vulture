"""Signal generator plot panel for real-time frequency/power visualization."""

import tkinter as tk
from tkinter import ttk
from typing import Sequence

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D


class SignalGeneratorPlotPanel(ttk.Frame):
    """
    Panel for displaying signal generator frequency and power plots.

    Embeds matplotlib figure with dual y-axis for frequency and power,
    plus a vertical line indicator showing current test position.
    """

    def __init__(self, parent: tk.Widget, **kwargs):
        """
        Initialize signal generator plot panel.

        Args:
            parent: Parent widget
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        # Data storage
        self._times: list[float] = []
        self._frequencies: list[float] = []
        self._powers: list[float] = []

        # Position indicator
        self._position_line: Line2D | None = None

        # Y-axis scale state: 'linear' or 'log'
        # Frequency defaults to log scale; power (dBm) defaults to linear
        self._freq_scale: str = "log"
        self._power_scale: str = "linear"

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create matplotlib figure and canvas."""
        # Create figure with constrained layout
        self._figure = Figure(figsize=(8, 4), dpi=100)
        self._figure.tight_layout()

        # Primary axis for frequency
        self._ax_freq = self._figure.add_subplot(111)
        self._ax_freq.set_xlabel("Time (s)")
        self._ax_freq.set_ylabel("Frequency (Hz)", color="green")
        self._ax_freq.tick_params(axis="y", labelcolor="green")
        self._ax_freq.grid(True, alpha=0.3)

        # Secondary axis for power
        self._ax_power = self._ax_freq.twinx()
        self._ax_power.set_ylabel("Power (dBm)", color="orange")
        self._ax_power.tick_params(axis="y", labelcolor="orange")

        # Create plot lines (steps-post holds value constant until next point)
        (self._freq_line,) = self._ax_freq.plot(
            [], [], "g-", label="Frequency", linewidth=2, drawstyle="steps-post"
        )
        (self._power_line,) = self._ax_power.plot(
            [],
            [],
            color="orange",
            linestyle="-",
            label="Power",
            linewidth=2,
            drawstyle="steps-post",
        )

        # Legend
        lines = [self._freq_line, self._power_line]
        labels = [str(line.get_label()) for line in lines]
        self._ax_freq.legend(lines, labels, loc="upper left")

        # Apply default log scale for frequency axis
        self._ax_freq.set_yscale("log")
        self._ax_freq.set_ylabel("Frequency (Hz) (log)", color="green")

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

    def add_point(self, time: float, frequency: float, power: float) -> None:
        """
        Add a data point to the plot.

        Args:
            time: Time in seconds
            frequency: Frequency in Hz
            power: Power in dBm
        """
        self._times.append(time)
        self._frequencies.append(frequency)
        self._powers.append(power)

        self._update_plot()

    def set_data(
        self,
        times: Sequence[float],
        frequencies: Sequence[float],
        powers: Sequence[float],
    ) -> None:
        """
        Replace all plot data (used to show full test plan).

        Args:
            times: Time values
            frequencies: Frequency values in Hz
            powers: Power values in dBm
        """
        self._times = list(times)
        self._frequencies = list(frequencies)
        self._powers = list(powers)

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
            self._position_line = self._ax_freq.axvline(
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

        freq_label = (
            "Frequency Y-Axis: Switch to Linear"
            if self._freq_scale == "log"
            else "Frequency Y-Axis: Switch to Log"
        )
        menu.add_command(label=freq_label, command=self._toggle_freq_scale)

        power_label = (
            "Power Y-Axis: Switch to Log"
            if self._power_scale == "linear"
            else "Power Y-Axis: Switch to Linear"
        )
        menu.add_command(label=power_label, command=self._toggle_power_scale)

        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_freq_scale(self) -> None:
        """Toggle frequency Y-axis between linear and log scale."""
        self._freq_scale = "log" if self._freq_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _toggle_power_scale(self) -> None:
        """Toggle power Y-axis between linear and log scale."""
        self._power_scale = "log" if self._power_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _apply_scales(self) -> None:
        """Apply current scale settings to axes and update labels."""
        self._ax_freq.set_yscale(self._freq_scale)
        self._ax_power.set_yscale(self._power_scale)

        freq_suffix = " (log)" if self._freq_scale == "log" else ""
        power_suffix = " (log)" if self._power_scale == "log" else ""
        self._ax_freq.set_ylabel(f"Frequency (Hz){freq_suffix}", color="green")
        self._ax_power.set_ylabel(f"Power (dBm){power_suffix}", color="orange")

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
                ax.set_ylim(max(0, v_min), v_max * 1.1 or 1)
            else:
                margin = (v_max - v_min) * 0.1 or 1
                ax.set_ylim(v_min - margin, v_max + margin)

    def _update_plot(self) -> None:
        """Update plot with current data."""
        # Update line data
        self._freq_line.set_data(self._times, self._frequencies)
        self._power_line.set_data(self._times, self._powers)

        # Adjust axis limits
        if self._times:
            self._ax_freq.set_xlim(0, max(self._times) * 1.05 or 1)

            if self._frequencies:
                self._set_ylim_for_scale(
                    self._ax_freq,
                    self._frequencies,
                    self._freq_scale,
                    lower_bound_zero=True,
                )

            if self._powers:
                self._set_ylim_for_scale(
                    self._ax_power,
                    self._powers,
                    self._power_scale,
                    lower_bound_zero=False,
                )

        # Redraw
        self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear all plot data and position indicator."""
        self._times.clear()
        self._frequencies.clear()
        self._powers.clear()

        self._freq_line.set_data([], [])
        self._power_line.set_data([], [])

        # Clear position line
        if self._position_line is not None:
            self._position_line.remove()
            self._position_line = None

        # Reset scales to defaults (frequency defaults to log)
        self._freq_scale = "log"
        self._power_scale = "linear"
        self._apply_scales()

        self._ax_freq.set_xlim(0, 1)
        self._ax_freq.set_ylim(1, 1000)
        self._ax_power.set_ylim(-20, 10)

        self._canvas.draw_idle()

    def set_title(self, title: str) -> None:
        """
        Set plot title.

        Args:
            title: Title text
        """
        self._ax_freq.set_title(title)
        self._canvas.draw_idle()

    def load_test_plan_preview(
        self,
        times: Sequence[float],
        frequencies: Sequence[float],
        powers: Sequence[float],
    ) -> None:
        """
        Load test plan data as a preview (shows full plan trajectory).

        Args:
            times: Time values
            frequencies: Frequency values in Hz
            powers: Power values in dBm
        """
        self.set_data(times, frequencies, powers)
        self.clear_position()
