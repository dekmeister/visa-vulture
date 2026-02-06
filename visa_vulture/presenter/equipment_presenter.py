"""Equipment presenter - coordinates model and view."""

import logging

from ..config import ValidationLimits
from ..file_io import read_test_plan
from ..instruments import InstrumentEntry
from ..model import (
    EquipmentModel,
    EquipmentState,
    TestStep,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)
from ..utils import BackgroundTaskRunner, TaskResult
from ..view import MainWindow
from .timer_manager import TimerManager

logger = logging.getLogger(__name__)


class EquipmentPresenter:
    """
    Coordinates model and view.

    Wires view callbacks to model operations.
    Manages background thread execution for VISA operations.
    Updates view based on model state changes.
    """

    def __init__(
        self,
        model: EquipmentModel,
        view: MainWindow,
        poll_interval_ms: int = 100,
        plot_refresh_interval_ms: int = 1000,
        validation_limits: ValidationLimits | None = None,
        instrument_registry: dict[str, InstrumentEntry] | None = None,
    ):
        """
        Initialize presenter.

        Args:
            model: Equipment model
            view: Main window view
            poll_interval_ms: Polling interval for background task results
            plot_refresh_interval_ms: Interval for plot position updates during test
            validation_limits: Optional soft validation limits for test plans.
                If provided, values exceeding soft limits generate warnings.
            instrument_registry: Optional registry of available instrument types.
                Maps display names to InstrumentEntry objects. If not provided,
                only built-in instrument types are available.
        """
        self._model = model
        self._view = view
        self._poll_interval_ms = poll_interval_ms
        self._plot_refresh_interval_ms = plot_refresh_interval_ms
        self._validation_limits = validation_limits
        self._instrument_registry = instrument_registry

        # Background task runner
        self._task_runner = BackgroundTaskRunner(view.schedule)

        # Timer management (runtime display + plot refresh)
        self._timer = TimerManager(
            view.schedule, view.cancel_schedule, plot_refresh_interval_ms
        )

        # Pending "start from" state (step, remaining_duration)
        self._pending_start_from: tuple[int, float] | None = None

        # Flag to suppress next completion callback (used during Resume From)
        self._suppress_next_completion: bool = False

        # Wire everything up
        self._wire_callbacks()
        self._task_runner.start(poll_interval_ms)

        # Initial view state
        self._update_view_for_state(self._model.state)

        logger.info("EquipmentPresenter initialized")

    def _wire_callbacks(self) -> None:
        """Wire view callbacks and model callbacks."""
        # View callbacks
        self._view.set_on_connect(self._handle_connect)
        self._view.set_on_disconnect(self._handle_disconnect)
        self._view.set_on_load_test_plan(self._handle_load_test_plan)
        self._view.set_on_run(self._handle_run)
        self._view.set_on_stop(self._handle_stop)
        self._view.set_on_pause(self._handle_pause)
        self._view.set_on_start_from(self._handle_start_from)

        # Table selection callbacks
        self._view.ps_table.register_selection_callback(
            self._on_table_selection_changed
        )
        self._view.sg_table.register_selection_callback(
            self._on_table_selection_changed
        )

        # Model callbacks
        self._model.register_state_callback(self._on_state_changed)
        self._model.register_progress_callback(self._on_test_progress)
        self._model.register_complete_callback(self._on_test_complete)

    # View callback handlers

    def _handle_connect(self) -> None:
        """Handle connect button - opens resource manager dialog."""
        from ..view import ResourceManagerDialog

        logger.info("Connect requested - opening resource manager")

        # Build instrument type list for the dialog dropdown
        instrument_types = None
        if self._instrument_registry:
            instrument_types = list(self._instrument_registry.keys())

        # Create and configure dialog
        dialog = ResourceManagerDialog(
            self._view._root, instrument_types=instrument_types
        )
        dialog.set_on_scan(lambda: self._handle_dialog_scan(dialog))
        dialog.set_on_identify(lambda: self._handle_dialog_identify(dialog))

        # Show dialog and wait for result
        result = dialog.show()

        if result is None:
            logger.info("Connection cancelled")
            return

        resource_address, selected_display_name = result

        # Resolve the selected instrument type through the registry
        instrument_class = None
        if (
            self._instrument_registry
            and selected_display_name in self._instrument_registry
        ):
            entry = self._instrument_registry[selected_display_name]
            instrument_type = entry.base_type
            # Only pass custom class for non-built-in instruments
            if selected_display_name not in ("Power Supply", "Signal Generator"):
                instrument_class = entry.cls
        else:
            # Fallback for when no registry is available
            if selected_display_name == "Signal Generator":
                instrument_type = "signal_generator"
            else:
                instrument_type = "power_supply"

        self._connect_to_resource(resource_address, instrument_type, instrument_class)

    def _handle_dialog_scan(self, dialog) -> None:
        """Handle Scan button in resource manager dialog."""
        dialog.set_status("Scanning...")
        dialog.set_buttons_enabled(False, False, False)

        def task():
            return self._model.scan_resources()

        def on_complete(result):
            if isinstance(result, TaskResult) and not result.success:
                dialog.set_status(f"Scan failed: {result.error}")
                dialog.set_resources([])
                dialog.set_buttons_enabled(True, False, False)
            else:
                dialog.set_resources(result)
                has_resources = len(result) > 0
                dialog.set_status(f"Found {len(result)} resource(s)")
                dialog.set_buttons_enabled(True, has_resources, has_resources)

        self._task_runner.run_task(task, on_complete)

    def _handle_dialog_identify(self, dialog) -> None:
        """Handle Identify button - query *IDN? on each resource."""
        resources = dialog.get_resources()
        if not resources:
            dialog.set_status("No resources to identify")
            return

        dialog.set_status("Identifying resources...")
        dialog.set_buttons_enabled(False, False, False)

        def task():
            results = {}
            for resource in resources:
                results[resource] = self._model.identify_resource(resource)
            return results

        def on_complete(result):
            if isinstance(result, TaskResult) and not result.success:
                dialog.set_status(f"Identify failed: {result.error}")
            else:
                for resource, idn in result.items():
                    dialog.set_resource_identification(resource, idn)
                dialog.set_status("Identification complete")
            dialog.set_buttons_enabled(True, True, True)

        self._task_runner.run_task(task, on_complete)

    def _connect_to_resource(
        self,
        resource_address: str,
        instrument_type: str,
        instrument_class: type | None = None,
    ) -> None:
        """Connect to selected resource."""
        logger.info("Connecting to %s as %s", resource_address, instrument_type)
        self._view.set_status(f"Connecting to {resource_address}...")

        def task():
            self._model.connect_instrument(
                resource_address,
                instrument_type,
                instrument_class=instrument_class,
            )

        def on_complete(result):
            if isinstance(result, TaskResult) and not result.success:
                self._view.show_error("Connection Error", str(result.error))
                self._view.set_status("Connection failed")
            else:
                self._view.set_connection_status(True)
                self._view.set_status("Connected")
                self._update_instrument_display()
                # Show only relevant tab
                if instrument_type == "power_supply":
                    self._view.show_power_supply_tab_only()
                else:
                    self._view.show_signal_generator_tab_only()

        self._task_runner.run_task(task, on_complete)

    def _handle_disconnect(self) -> None:
        """Handle disconnect button."""
        logger.info("Disconnect requested")
        self._view.set_status("Disconnecting...")

        def task():
            self._model.disconnect()

        def on_complete(result):
            self._view.set_connection_status(False)
            self._view.set_status("Disconnected")
            self._view.set_instrument_display(None, None)
            # Show both tabs when disconnected
            self._view.show_all_tabs()

        self._task_runner.run_task(task, on_complete)

    def _handle_load_test_plan(self, file_path: str) -> None:
        """Handle load test plan button."""
        logger.info("Loading test plan: %s", file_path)

        result = read_test_plan(file_path, soft_limits=self._validation_limits)

        if result.errors:
            error_msg = "\n".join(result.errors)
            self._view.show_error("Test Plan Error", error_msg)
            logger.error("Test plan load failed: %s", error_msg)
            return

        test_plan = result.plan
        if test_plan is None:
            self._view.show_error("Test Plan Error", "Failed to load test plan")
            return

        # Check instrument type match if connected
        mismatch = self._check_instrument_type_match(test_plan.plan_type)
        if mismatch is not None:
            logger.error("Test plan load failed: %s", mismatch)
            self._view.show_error("Instrument Mismatch", mismatch)
            return

        # Log warnings if any
        if result.warnings:
            for warning in result.warnings:
                logger.warning("Test plan warning: %s", warning)
            # Show warnings to user but allow proceeding
            warning_msg = "\n".join(result.warnings)
            self._view.show_warning(
                "Test Plan Warnings",
                f"The test plan was loaded but has warnings:\n\n{warning_msg}",
            )

        try:
            self._model.load_test_plan(test_plan)
            self._view.set_test_plan_name(test_plan.name)
            self._view.set_status(f"Loaded: {test_plan}")

            # Handle plot and table based on plan type
            if test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                self._setup_signal_generator_preview(test_plan)
            else:
                self._setup_power_supply_preview(test_plan)

            # Enable run button if connected
            if self._model.state == EquipmentState.IDLE:
                self._view.set_buttons_for_state("IDLE")

            # Show total duration as remaining time
            self._view.set_remaining_time_display(test_plan.total_duration)

            logger.info("Test plan loaded: %s", test_plan)

        except ValueError as e:
            self._view.show_error("Test Plan Error", str(e))
            logger.error("Test plan validation failed: %s", e)

    def _handle_run(self) -> None:
        """Handle run button (also handles resume when paused)."""
        # Handle resume from paused state
        if self._model.state == EquipmentState.PAUSED:
            logger.info("Resume requested")
            self._model.resume_test()
            self._view.set_status("Resuming test...")

            # Restore runtime timer from where we left off
            self._timer.resume(self._update_runtime, self._update_plot_position)
            return

        logger.info("Run requested")

        if self._model.test_plan is None:
            self._view.show_error("Error", "No test plan loaded")
            return

        # Verify instrument type matches plan type
        mismatch = self._check_instrument_type_match(self._model.test_plan.plan_type)
        if mismatch is not None:
            self._view.show_error("Instrument Mismatch", mismatch)
            return

        self._view.set_status("Running test...")

        # Start runtime timer
        self._timer.start(self._update_runtime, self._update_plot_position)

        # Clear position indicator but keep the plan preview for both plot types
        if self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            self._view.signal_gen_plot_panel.clear_position()
        else:
            self._view.power_supply_plot_panel.clear_position()

        def task():
            self._model.run_test()

        def on_complete(result):
            # State change callback handles UI updates
            pass

        self._task_runner.run_task(task, on_complete)

    def _handle_stop(self) -> None:
        """Handle stop button."""
        logger.info("Stop requested")
        self._model.stop_test()
        self._view.set_status("Stopping...")
        # Clear pause state if stopping from paused
        self._timer.clear_pause_state()

    def _handle_pause(self) -> None:
        """Handle pause button."""
        logger.info("Pause requested")
        self._model.pause_test()
        self._view.set_status("Pausing...")

    def _on_table_selection_changed(self, step_number: int | None) -> None:
        """Handle table row selection change to enable/disable Start from button."""
        state = self._model.state
        has_plan = self._model.test_plan is not None
        if (
            state in (EquipmentState.IDLE, EquipmentState.PAUSED)
            and step_number is not None
            and has_plan
        ):
            self._view.set_start_from_enabled(True)
        else:
            self._view.set_start_from_enabled(False)

    def _handle_start_from(self) -> None:
        """Handle Start from / Resume from button click."""
        selected_step = self._view.get_active_table_selected_step()
        if selected_step is None:
            self._view.show_error("Error", "No test step selected")
            return

        if self._model.test_plan is None:
            self._view.show_error("Error", "No test plan loaded")
            return

        step = self._model.test_plan.get_step(selected_step)
        if step is None:
            self._view.show_error("Error", f"Step {selected_step} not found")
            return

        # Build confirmation message
        remaining_duration = self._model.test_plan.duration_from_step(selected_step)
        total_steps = self._model.test_plan.step_count
        steps_to_run = total_steps - selected_step + 1

        if isinstance(step, PowerSupplyTestStep):
            step_details = f"V={step.voltage:.2f}V, I={step.current:.2f}A"
        elif isinstance(step, SignalGeneratorTestStep):
            step_details = f"F={step.frequency:.1f} Hz, P={step.power:.1f} dBm"
        else:
            step_details = f"Duration={step.duration_seconds}s"

        is_paused = self._model.state == EquipmentState.PAUSED
        action = "Resume from" if is_paused else "Start from"

        remaining_int = max(0, int(remaining_duration))
        minutes = remaining_int // 60
        seconds = remaining_int % 60
        duration_str = f"{minutes:02d}:{seconds:02d}"

        message = (
            f"{action} step {selected_step}/{total_steps}?\n\n"
            f"Step details: {step_details}\n"
            f"Description: {step.description}\n"
            f"Steps remaining: {steps_to_run}\n"
            f"Estimated duration: {duration_str}"
        )

        if not self._view.show_confirmation(f"{action} Step {selected_step}", message):
            return

        if is_paused:
            self._pending_start_from = (selected_step, remaining_duration)
            self._model.stop_test()
            self._timer.clear_pause_state()
            self._view.set_status(f"Restarting from step {selected_step}...")
            return

        # IDLE state - start directly
        self._execute_start_from(selected_step, remaining_duration)

    def _execute_start_from(self, start_step: int, remaining_duration: float) -> None:
        """Execute test from a specific step with adjusted timer."""
        logger.info("Starting test from step %d", start_step)
        self._view.set_status(f"Running from step {start_step}...")

        self._timer.start_from(
            remaining_duration, self._update_runtime, self._update_plot_position
        )

        if (
            self._model.test_plan is not None
            and self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
        ):
            self._view.signal_gen_plot_panel.clear_position()
        else:
            self._view.power_supply_plot_panel.clear_position()

        def task():
            self._model.run_test(start_step)

        def on_complete(result):
            pass

        self._task_runner.run_task(task, on_complete)

    # Model callback handlers

    def _on_state_changed(
        self, old_state: EquipmentState, new_state: EquipmentState
    ) -> None:
        """Handle model state change."""
        logger.debug("State changed: %s -> %s", old_state.name, new_state.name)

        # Handle timers when leaving RUNNING state
        if old_state == EquipmentState.RUNNING and new_state != EquipmentState.RUNNING:
            self._timer.stop_plot_refresh()
            if new_state == EquipmentState.PAUSED:
                # Pausing - save elapsed time (on callback thread for accuracy),
                # then cancel timer scheduling on main thread
                self._timer.save_pause_state()
                self._view.schedule(0, self._timer.cancel_runtime_timer)
            else:
                # Actually stopping
                self._timer.clear_pause_state()
                self._view.schedule(0, self._stop_and_reset_display)

        # Clear pause state when transitioning from PAUSED to IDLE (stop while paused)
        if old_state == EquipmentState.PAUSED and new_state == EquipmentState.IDLE:
            self._timer.clear_pause_state()

        # Handle pending "start from" operation (after stopping a paused run)
        if new_state == EquipmentState.IDLE and self._pending_start_from is not None:
            start_step, remaining_duration = self._pending_start_from
            self._pending_start_from = None
            self._suppress_next_completion = True  # Suppress the "stopped" completion

            def start_from_callback(
                s: int = start_step, d: float = remaining_duration
            ) -> None:
                self._execute_start_from(s, d)

            self._view.schedule(50, start_from_callback)

        # Schedule view update on main thread
        self._view.schedule(0, lambda: self._update_view_for_state(new_state))

    def _on_test_progress(self, current: int, total: int, step: TestStep) -> None:
        """Handle test progress update."""

        # Schedule view update on main thread
        def update():
            if isinstance(step, SignalGeneratorTestStep):
                # Signal generator step
                self._view.set_status(
                    f"Step {current}/{total}: F={step.frequency/1e6:.3f} MHz, P={step.power:.1f} dBm"
                )
                # Update position indicator on the plot
                self._view.signal_gen_plot_panel.set_current_position(
                    step.absolute_time_seconds
                )
                # Highlight current row in table
                self._view.sg_table.highlight_step(step.step_number)
            elif isinstance(step, PowerSupplyTestStep):
                # Power supply step
                self._view.set_status(
                    f"Step {current}/{total}: V={step.voltage:.2f}V, I={step.current:.2f}A"
                )
                # Update position indicator on the plot
                self._view.power_supply_plot_panel.set_current_position(
                    step.absolute_time_seconds
                )
                # Highlight current row in table
                self._view.ps_table.highlight_step(step.step_number)

        self._view.schedule(0, update)

    def _on_test_complete(self, success: bool, message: str) -> None:
        """Handle test completion."""
        # Check if this completion should be suppressed (Resume From operation)
        if self._suppress_next_completion:
            self._suppress_next_completion = False
            return

        def update():
            if success:
                self._view.set_status(message)
                self._view.show_info("Test Complete", message)
            else:
                self._view.set_status(f"Error: {message}")
                self._view.show_error("Test Error", message)

            # Clear position indicators and table highlighting
            if (
                self._model.test_plan
                and self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR
            ):
                self._view.signal_gen_plot_panel.clear_position()
                self._view.sg_table.clear_highlight()
            else:
                self._view.power_supply_plot_panel.clear_position()
                self._view.ps_table.clear_highlight()

        self._view.schedule(0, update)

    def _update_instrument_display(self) -> None:
        """Update instrument identification display."""
        if self._model.state not in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            self._view.set_instrument_display(None, None)
            return

        # Single instrument - no need to check tab
        model_name, tooltip = self._model.get_instrument_identification()
        self._view.set_instrument_display(model_name, tooltip)

    def _check_instrument_type_match(self, plan_type: str) -> str | None:
        """Check if the plan type is compatible with the connected instrument.

        Returns an error message if mismatched, or None if compatible.
        """
        if self._model.is_plan_type_compatible(plan_type):
            return None
        plan_label = plan_type.replace("_", " ")
        instrument_label = (self._model.instrument_type or "").replace("_", " ")
        return (
            f"Cannot load {plan_label} test plan: "
            f"connected instrument is a {instrument_label}"
        )

    def _setup_signal_generator_preview(self, test_plan) -> None:
        """Set up signal generator plot and table for a loaded test plan."""
        self._view.signal_gen_plot_panel.clear()
        self._view.signal_gen_plot_panel.set_title(test_plan.name)
        self._view.show_signal_generator_plot()

        times = [s.absolute_time_seconds for s in test_plan.steps]
        freqs = [s.frequency for s in test_plan.steps]  # type: ignore[attr-defined]
        powers = [s.power for s in test_plan.steps]  # type: ignore[attr-defined]
        self._view.signal_gen_plot_panel.load_test_plan_preview(times, freqs, powers)
        self._view.sg_table.load_steps(test_plan.steps)

    def _setup_power_supply_preview(self, test_plan) -> None:
        """Set up power supply plot and table for a loaded test plan."""
        self._view.power_supply_plot_panel.clear()
        self._view.power_supply_plot_panel.set_title(test_plan.name)
        self._view.show_power_supply_plot()

        times = [s.absolute_time_seconds for s in test_plan.steps]
        voltages = [s.voltage for s in test_plan.steps]  # type: ignore[attr-defined]
        currents = [s.current for s in test_plan.steps]  # type: ignore[attr-defined]
        self._view.power_supply_plot_panel.load_test_plan_preview(
            times, voltages, currents
        )
        self._view.ps_table.load_steps(test_plan.steps)

    def _update_view_for_state(self, state: EquipmentState) -> None:
        """Update view based on current state."""
        state_name = state.name

        self._view.set_state_display(state_name)
        self._view.set_buttons_for_state(state_name)

        # Update connection indicator
        connected = state in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        )
        self._view.set_connection_status(connected)

        # Check if run should be enabled (need both connection and test plan)
        if state == EquipmentState.IDLE and self._model.test_plan is None:
            # Can't run without a test plan, but leave button state for visual feedback
            pass

        # Update "Start from" button based on selection and state
        if state in (EquipmentState.IDLE, EquipmentState.PAUSED):
            selected = self._view.get_active_table_selected_step()
            has_plan = self._model.test_plan is not None
            self._view.set_start_from_enabled(selected is not None and has_plan)

    # Timer tick callbacks (called by TimerManager, need model/view access)

    def _update_runtime(self) -> None:
        """Update runtime display and schedule next update."""
        elapsed = self._timer.get_elapsed()
        if elapsed is not None and self._model.test_plan is not None:
            elapsed_int = int(elapsed)
            total = (
                self._timer.partial_total_duration
                or self._model.test_plan.total_duration
            )
            remaining = max(0.0, total - elapsed_int)
            self._view.set_runtime_display(elapsed_int)
            self._view.set_remaining_time_display(remaining)
            self._timer.schedule_runtime_tick(self._update_runtime)

    def _update_plot_position(self) -> None:
        """Update plot position indicator based on elapsed time."""
        elapsed = self._timer.get_elapsed()
        if elapsed is None or self._model.test_plan is None:
            return

        # If running partial plan, adjust for offset
        partial = self._timer.partial_total_duration
        if partial is not None:
            total = self._model.test_plan.total_duration
            offset = total - partial
            current_time = offset + elapsed
        else:
            current_time = elapsed

        # Update the appropriate plot
        if self._model.test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
            self._view.signal_gen_plot_panel.set_current_position(current_time)
        else:
            self._view.power_supply_plot_panel.set_current_position(current_time)

        self._timer.schedule_plot_tick(self._update_plot_position)

    def _stop_and_reset_display(self) -> None:
        """Stop all timers and reset runtime/remaining displays."""
        self._timer.stop()
        self._view.set_runtime_display(None)
        if self._model.test_plan is not None:
            self._view.set_remaining_time_display(self._model.test_plan.total_duration)
        else:
            self._view.set_remaining_time_display(None)

    def shutdown(self) -> None:
        """Clean shutdown of presenter."""
        logger.info("EquipmentPresenter shutting down")
        self._stop_and_reset_display()
        self._task_runner.stop()

        # Disconnect if connected
        if self._model.state in (
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            try:
                self._model.disconnect()
            except Exception as e:
                logger.warning("Error during disconnect on shutdown: %s", e)
