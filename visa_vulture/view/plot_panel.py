"""Plot panel widget for real-time dual-axis data visualization."""

import tkinter as tk
from tkinter import ttk
from typing import Sequence

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ..instrument_specs import AxisConfig


class PlotPanel(ttk.Frame):
    """
    Panel for displaying real-time dual-axis plots.

    Embeds a matplotlib figure with dual y-axes. The primary and secondary
    axis configurations (labels, colors, scales, limits) are supplied at
    construction time as ``AxisConfig`` data, so the panel is generic across
    instrument types.
    """

    def __init__(
        self,
        parent: tk.Widget,
        primary: AxisConfig,
        secondary: AxisConfig,
        **kwargs,
    ):
        """
        Initialize plot panel.

        Args:
            parent: Parent widget
            primary: Configuration for the primary (left) Y-axis
            secondary: Configuration for the secondary (right) Y-axis
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self._primary = primary
        self._secondary = secondary

        # Data storage
        self._times: list[float] = []
        self._primary_values: list[float] = []
        self._secondary_values: list[float] = []

        # Position indicator
        self._position_line: Line2D | None = None

        # Y-axis scale state: 'linear' or 'log'
        self._primary_scale: str = self._primary.default_scale
        self._secondary_scale: str = self._secondary.default_scale

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create matplotlib figure and canvas."""
        # Create figure with constrained layout
        self._figure = Figure(figsize=(8, 4), dpi=100)
        self._figure.tight_layout()

        # Primary axis
        self._ax_primary = self._figure.add_subplot(111)
        self._ax_primary.set_xlabel("Time (s)")
        self._ax_primary.set_ylabel(self._primary.label, color=self._primary.color)
        self._ax_primary.tick_params(axis="y", labelcolor=self._primary.color)
        self._ax_primary.grid(True, alpha=0.3)

        # Secondary axis
        self._ax_secondary = self._ax_primary.twinx()
        self._ax_secondary.set_ylabel(
            self._secondary.label, color=self._secondary.color
        )
        self._ax_secondary.tick_params(axis="y", labelcolor=self._secondary.color)

        # Create plot lines (steps-post holds value constant until next point)
        (self._primary_line,) = self._ax_primary.plot(
            [],
            [],
            color=self._primary.color,
            linestyle="-",
            label=self._primary.legend_label,
            linewidth=2,
            drawstyle="steps-post",
        )
        (self._secondary_line,) = self._ax_secondary.plot(
            [],
            [],
            color=self._secondary.color,
            linestyle="-",
            label=self._secondary.legend_label,
            linewidth=2,
            drawstyle="steps-post",
        )

        # Legend
        lines = [self._primary_line, self._secondary_line]
        labels = [str(line.get_label()) for line in lines]
        self._ax_primary.legend(lines, labels, loc="upper left")

        # Apply default scales (handles non-linear defaults like log)
        self._apply_scales()

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

    def add_point(
        self, time: float, primary_value: float, secondary_value: float
    ) -> None:
        """
        Add a data point to the plot.

        Args:
            time: Time in seconds
            primary_value: Primary axis reading
            secondary_value: Secondary axis reading
        """
        self._times.append(time)
        self._primary_values.append(primary_value)
        self._secondary_values.append(secondary_value)

        self._update_plot()

    def set_data(
        self,
        times: Sequence[float],
        primary_values: Sequence[float],
        secondary_values: Sequence[float],
    ) -> None:
        """
        Replace all plot data.

        Args:
            times: Time values
            primary_values: Primary axis values
            secondary_values: Secondary axis values
        """
        self._times = list(times)
        self._primary_values = list(primary_values)
        self._secondary_values = list(secondary_values)

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
            self._position_line = self._ax_primary.axvline(
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

    def set_title(self, title: str) -> None:
        """
        Set plot title.

        Args:
            title: Title text
        """
        self._ax_primary.set_title(title)
        self._canvas.draw_idle()

    def clear(self) -> None:
        """Clear all plot data and position indicator."""
        self._times.clear()
        self._primary_values.clear()
        self._secondary_values.clear()

        self._primary_line.set_data([], [])
        self._secondary_line.set_data([], [])

        # Clear position line
        if self._position_line is not None:
            self._position_line.remove()
            self._position_line = None

        # Reset scales to defaults
        self._primary_scale = self._primary.default_scale
        self._secondary_scale = self._secondary.default_scale
        self._apply_scales()

        self._ax_primary.set_xlim(0, 1)
        self._ax_primary.set_ylim(*self._primary.default_ylim)
        self._ax_secondary.set_ylim(*self._secondary.default_ylim)

        self._canvas.draw_idle()

    def load_test_plan_preview(
        self,
        times: Sequence[float],
        primary_values: Sequence[float],
        secondary_values: Sequence[float],
    ) -> None:
        """
        Load test plan data as a preview (shows full plan trajectory).

        Args:
            times: Time values
            primary_values: Primary axis values
            secondary_values: Secondary axis values
        """
        self.set_data(times, primary_values, secondary_values)
        self.clear_position()

    def _show_scale_menu(self, event: "tk.Event[tk.Widget]") -> None:
        """Show right-click context menu for Y-axis scale selection."""
        menu = tk.Menu(self, tearoff=0)

        if not self._primary.linear_only:
            primary_label = (
                f"{self._primary.legend_label} Y-Axis: Switch to Log"
                if self._primary_scale == "linear"
                else f"{self._primary.legend_label} Y-Axis: Switch to Linear"
            )
            menu.add_command(label=primary_label, command=self._toggle_primary_scale)

        if not self._secondary.linear_only:
            secondary_label = (
                f"{self._secondary.legend_label} Y-Axis: Switch to Log"
                if self._secondary_scale == "linear"
                else f"{self._secondary.legend_label} Y-Axis: Switch to Linear"
            )
            menu.add_command(
                label=secondary_label, command=self._toggle_secondary_scale
            )

        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_primary_scale(self) -> None:
        """Toggle primary Y-axis between linear and log scale."""
        self._primary_scale = "log" if self._primary_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _toggle_secondary_scale(self) -> None:
        """Toggle secondary Y-axis between linear and log scale."""
        self._secondary_scale = "log" if self._secondary_scale == "linear" else "linear"
        self._apply_scales()
        self._update_plot()

    def _apply_scales(self) -> None:
        """Apply current scale settings to axes and update labels."""
        self._ax_primary.set_yscale(self._primary_scale)
        self._ax_secondary.set_yscale(self._secondary_scale)

        primary_suffix = " (log)" if self._primary_scale == "log" else ""
        secondary_suffix = " (log)" if self._secondary_scale == "log" else ""
        self._ax_primary.set_ylabel(
            f"{self._primary.label}{primary_suffix}", color=self._primary.color
        )
        self._ax_secondary.set_ylabel(
            f"{self._secondary.label}{secondary_suffix}",
            color=self._secondary.color,
        )

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
        self._primary_line.set_data(self._times, self._primary_values)
        self._secondary_line.set_data(self._times, self._secondary_values)

        # Adjust axis limits
        if self._times:
            self._ax_primary.set_xlim(0, max(self._times) * 1.05 or 1)

            if self._primary_values:
                self._set_ylim_for_scale(
                    self._ax_primary,
                    self._primary_values,
                    self._primary_scale,
                    lower_bound_zero=self._primary.lower_bound_zero,
                )

            if self._secondary_values:
                self._set_ylim_for_scale(
                    self._ax_secondary,
                    self._secondary_values,
                    self._secondary_scale,
                    lower_bound_zero=self._secondary.lower_bound_zero,
                )

        # Redraw
        self._canvas.draw_idle()
