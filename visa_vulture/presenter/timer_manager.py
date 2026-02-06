"""Timer management for test execution timing and plot refresh."""

import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)

ScheduleFn = Callable[[int, Callable[[], None]], str]
CancelFn = Callable[[str], None]


class TimerManager:
    """
    Manages runtime and plot refresh timers during test execution.

    Encapsulates all timer state: start time, pause elapsed time,
    partial total duration (for "start from" operations), and timer IDs.

    The presenter provides tick callbacks that handle display updates;
    this class handles the lifecycle (start, pause, resume, stop) and
    scheduling bookkeeping.

    This class does NOT reference the model or view directly. It uses
    injected schedule/cancel functions for Tkinter-safe timing.
    """

    def __init__(
        self,
        schedule_fn: ScheduleFn,
        cancel_fn: CancelFn,
        plot_refresh_interval_ms: int = 1000,
    ) -> None:
        self._schedule_fn = schedule_fn
        self._cancel_fn = cancel_fn
        self._plot_refresh_interval_ms = plot_refresh_interval_ms

        # Runtime timer state
        self._runtime_timer_id: str | None = None
        self._run_start_time: float | None = None
        self._elapsed_at_pause: float | None = None
        self._partial_total_duration: float | None = None

        # Plot refresh timer state
        self._plot_refresh_timer_id: str | None = None

    # --- Properties for read access (used by presenter tick callbacks and tests) ---

    @property
    def run_start_time(self) -> float | None:
        return self._run_start_time

    @property
    def elapsed_at_pause(self) -> float | None:
        return self._elapsed_at_pause

    @elapsed_at_pause.setter
    def elapsed_at_pause(self, value: float | None) -> None:
        self._elapsed_at_pause = value

    @property
    def partial_total_duration(self) -> float | None:
        return self._partial_total_duration

    @property
    def runtime_timer_id(self) -> str | None:
        return self._runtime_timer_id

    # --- Lifecycle methods ---

    def start(
        self,
        runtime_tick: Callable[[], None],
        plot_tick: Callable[[], None],
    ) -> None:
        """Start timers for a fresh run (from step 1)."""
        self._partial_total_duration = None
        self._run_start_time = time.time()
        runtime_tick()
        plot_tick()

    def start_from(
        self,
        remaining_duration: float,
        runtime_tick: Callable[[], None],
        plot_tick: Callable[[], None],
    ) -> None:
        """Start timers for a partial run (from a specific step)."""
        self._partial_total_duration = remaining_duration
        self._run_start_time = time.time()
        runtime_tick()
        plot_tick()

    def resume(
        self,
        runtime_tick: Callable[[], None],
        plot_tick: Callable[[], None],
    ) -> bool:
        """
        Resume timers after pause.

        Returns True if resumed (had saved elapsed time), False otherwise.
        """
        if self._elapsed_at_pause is None:
            return False
        self._run_start_time = time.time() - self._elapsed_at_pause
        self._elapsed_at_pause = None
        runtime_tick()
        plot_tick()
        return True

    def save_pause_state(self) -> None:
        """Save elapsed time when transitioning to PAUSED. Thread-safe."""
        if self._run_start_time is not None:
            self._elapsed_at_pause = time.time() - self._run_start_time

    def cancel_runtime_timer(self) -> None:
        """Cancel the runtime timer scheduling. Must call from main thread."""
        if self._runtime_timer_id is not None:
            self._cancel_fn(self._runtime_timer_id)
            self._runtime_timer_id = None

    def stop(self) -> None:
        """Full stop: cancel all timers, reset all state."""
        if self._runtime_timer_id is not None:
            self._cancel_fn(self._runtime_timer_id)
            self._runtime_timer_id = None
        self._stop_plot_refresh()
        self._run_start_time = None
        self._elapsed_at_pause = None
        self._partial_total_duration = None

    def stop_plot_refresh(self) -> None:
        """Stop the plot refresh timer."""
        self._stop_plot_refresh()

    def clear_pause_state(self) -> None:
        """Clear pause-related state without affecting timers."""
        self._elapsed_at_pause = None

    # --- Elapsed time calculation ---

    def get_elapsed(self) -> float | None:
        """Get current elapsed seconds, or None if not running."""
        if self._run_start_time is None:
            return None
        return time.time() - self._run_start_time

    # --- Recurring schedule helpers (called by presenter tick callbacks) ---

    def schedule_runtime_tick(self, callback: Callable[[], None]) -> None:
        """Schedule the next runtime tick (1 second interval)."""
        self._runtime_timer_id = self._schedule_fn(1000, callback)

    def schedule_plot_tick(self, callback: Callable[[], None]) -> None:
        """Schedule the next plot refresh tick."""
        self._plot_refresh_timer_id = self._schedule_fn(
            self._plot_refresh_interval_ms, callback
        )

    # --- Private helpers ---

    def _stop_plot_refresh(self) -> None:
        """Stop periodic plot position updates."""
        if self._plot_refresh_timer_id is not None:
            self._cancel_fn(self._plot_refresh_timer_id)
            self._plot_refresh_timer_id = None
