"""Signal generator plot panel for real-time frequency/power visualization."""

import tkinter as tk
from tkinter import ttk
from typing import Sequence

import matplotlib

matplotlib.use("TkAgg")

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

        # Embed in Tkinter
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Toolbar
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill=tk.X)
        self._toolbar = NavigationToolbar2Tk(self._canvas, toolbar_frame)
        self._toolbar.update()

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

    def _update_plot(self) -> None:
        """Update plot with current data."""
        # Update line data
        self._freq_line.set_data(self._times, self._frequencies)
        self._power_line.set_data(self._times, self._powers)

        # Adjust axis limits
        if self._times:
            self._ax_freq.set_xlim(0, max(self._times) * 1.05 or 1)

            if self._frequencies:
                f_min = min(self._frequencies)
                f_max = max(self._frequencies)
                margin = (f_max - f_min) * 0.1 or f_max * 0.1 or 1
                self._ax_freq.set_ylim(max(0, f_min - margin), f_max + margin)

            if self._powers:
                p_min = min(self._powers)
                p_max = max(self._powers)
                margin = (p_max - p_min) * 0.1 or 1
                self._ax_power.set_ylim(p_min - margin, p_max + margin)

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

        self._ax_freq.set_xlim(0, 1)
        self._ax_freq.set_ylim(0, 1)
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
