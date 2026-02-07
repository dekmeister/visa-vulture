"""Helper classes and functions for presenter testing."""

from typing import Any, Callable
from unittest.mock import Mock

from visa_vulture.model import EquipmentState, TestStep
from visa_vulture.utils.threading_helpers import TaskResult


class SynchronousTaskRunner:
    """
    Synchronous replacement for BackgroundTaskRunner.

    Executes tasks immediately and calls on_complete synchronously,
    eliminating threading complexity in tests.
    """

    def __init__(self, poll_callback: Callable[[int, Callable[[], None]], str]) -> None:
        """Initialize with poll callback (typically view.schedule)."""
        self._poll_callback = poll_callback

    def start(self, poll_interval_ms: int = 100) -> None:
        """No-op for synchronous execution."""
        pass

    def stop(self) -> None:
        """No-op for synchronous execution."""
        pass

    def run_task(
        self,
        task: Callable[[], Any],
        on_complete: Callable[[Any], None],
    ) -> None:
        """Execute task immediately and call on_complete with result."""
        try:
            result = task()
            on_complete(result)
        except Exception as e:
            on_complete(TaskResult(success=False, error=e))


def trigger_view_callback(view: Mock, callback_name: str, *args: Any) -> None:
    """
    Invoke a callback that the presenter registered on the view.

    Args:
        view: Mock view with _callbacks dictionary
        callback_name: Name of the callback (e.g., "on_connect")
        *args: Arguments to pass to the callback
    """
    callback = view._callbacks.get(callback_name)
    if callback is not None:
        callback(*args)


def set_model_state(model: Mock, state: EquipmentState) -> None:
    """
    Set model state directly for test setup.

    Args:
        model: Mock model with _current_state attribute
        state: The EquipmentState to set
    """
    model._current_state = state


def trigger_state_change(
    model: Mock, old_state: EquipmentState, new_state: EquipmentState
) -> None:
    """
    Simulate a state change and trigger all registered callbacks.

    Args:
        model: Mock model with _state_callbacks list and _current_state
        old_state: Previous state
        new_state: New state to transition to
    """
    model._current_state = new_state
    for callback in model._state_callbacks:
        callback(old_state, new_state)


def trigger_progress(model: Mock, current: int, total: int, step: TestStep) -> None:
    """
    Simulate a progress update and trigger all registered callbacks.

    Args:
        model: Mock model with _progress_callbacks list
        current: Current step number
        total: Total number of steps
        step: The current TestStep being executed
    """
    for callback in model._progress_callbacks:
        callback(current, total, step)


def trigger_complete(model: Mock, success: bool, message: str) -> None:
    """
    Simulate test completion and trigger all registered callbacks.

    Args:
        model: Mock model with _complete_callbacks list
        success: Whether the test completed successfully
        message: Completion message
    """
    for callback in model._complete_callbacks:
        callback(success, message)


def setup_timer_running(presenter: Any, elapsed_seconds: float) -> None:
    """Set up presenter timer state as if a test has been running for elapsed_seconds.

    Centralises private timer attribute access so individual tests don't
    reach into timer internals.
    """
    import time

    presenter._timer._run_start_time = time.time() - elapsed_seconds
    presenter._timer._runtime_timer_id = "timer_active"


def setup_timer_paused(presenter: Any, elapsed_seconds: float) -> None:
    """Set up presenter timer state as if paused after running for elapsed_seconds."""
    presenter._timer._elapsed_at_pause = elapsed_seconds


def execute_scheduled_callbacks(view: Mock) -> None:
    """
    Execute all pending scheduled callbacks on the mock view.

    This simulates what would happen when Tkinter's after() fires.
    Clears the scheduled callbacks after execution.

    Args:
        view: Mock view with _scheduled_callbacks dictionary
    """
    # Copy to avoid modification during iteration
    callbacks = list(view._scheduled_callbacks.values())
    view._scheduled_callbacks.clear()
    for callback in callbacks:
        callback()
