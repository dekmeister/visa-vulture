"""Threading utilities for background task execution."""

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class TaskResult(Generic[T]):
    """Result of a background task."""

    success: bool
    value: T | None = None
    error: Exception | None = None


class BackgroundTaskRunner:
    """
    Runs tasks in background threads with result callbacks.

    Designed for Tkinter applications where VISA operations
    must not block the main thread.
    """

    def __init__(self, poll_callback: Callable[[int, Callable[[], None]], str]):
        """
        Initialize task runner.

        Args:
            poll_callback: Function to schedule polling (e.g., root.after)
                          Takes (delay_ms, callback) and returns timer ID
        """
        self._poll_callback = poll_callback
        self._result_queue: queue.Queue[tuple[Callable, TaskResult]] = queue.Queue()
        self._poll_timer: str | None = None
        self._running = False

    def start(self, poll_interval_ms: int = 100) -> None:
        """
        Start polling for results.

        Args:
            poll_interval_ms: How often to check for results
        """
        if self._running:
            return

        self._running = True
        self._poll_interval_ms = poll_interval_ms
        self._schedule_poll()
        logger.debug("BackgroundTaskRunner started")

    def stop(self) -> None:
        """Stop polling for results."""
        self._running = False
        logger.debug("BackgroundTaskRunner stopped")

    def _schedule_poll(self) -> None:
        """Schedule next poll."""
        if self._running:
            self._poll_timer = self._poll_callback(
                self._poll_interval_ms, self._poll_results
            )

    def _poll_results(self) -> None:
        """Check for and process completed task results."""
        # Process all available results
        while True:
            try:
                callback, result = self._result_queue.get_nowait()
                self._invoke_callback(callback, result)
            except queue.Empty:
                break

        # Schedule next poll
        self._schedule_poll()

    def _invoke_callback(self, callback: Callable, result: TaskResult) -> None:
        """Invoke callback with result, handling errors."""
        try:
            if result.success:
                callback(result.value)
            else:
                callback(result)
        except Exception as e:
            logger.error("Error in task callback: %s", e)

    def run_task(
        self,
        task: Callable[[], T],
        on_complete: Callable[[T | TaskResult], None],
    ) -> None:
        """
        Run a task in a background thread.

        Args:
            task: Function to run (no arguments)
            on_complete: Callback for result (receives value on success,
                        TaskResult on failure)
        """

        def worker():
            try:
                result = task()
                self._result_queue.put(
                    (on_complete, TaskResult(success=True, value=result))
                )
            except Exception as e:
                logger.error("Background task failed: %s", e)
                self._result_queue.put(
                    (on_complete, TaskResult(success=False, error=e))
                )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        logger.debug("Started background task: %s", task)

    def run_task_with_args(
        self,
        task: Callable[..., T],
        args: tuple = (),
        kwargs: dict | None = None,
        on_complete: Callable[[T | TaskResult], None] | None = None,
    ) -> None:
        """
        Run a task with arguments in a background thread.

        Args:
            task: Function to run
            args: Positional arguments
            kwargs: Keyword arguments
            on_complete: Optional callback for result
        """
        kwargs = kwargs or {}

        def worker():
            try:
                result = task(*args, **kwargs)
                if on_complete:
                    self._result_queue.put(
                        (on_complete, TaskResult(success=True, value=result))
                    )
            except Exception as e:
                logger.error("Background task failed: %s", e)
                if on_complete:
                    self._result_queue.put(
                        (on_complete, TaskResult(success=False, error=e))
                    )

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        logger.debug("Started background task: %s(*%s, **%s)", task, args, kwargs)
