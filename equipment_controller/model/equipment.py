"""Equipment model - core business logic."""

import logging
import time
from typing import Callable

from ..instruments import BaseInstrument, PowerSupply, VISAConnection
from .state_machine import EquipmentState, StateMachine
from .test_plan import TestPlan, TestStep

logger = logging.getLogger(__name__)


TestProgressCallback = Callable[[int, int, TestStep], None]
TestCompleteCallback = Callable[[bool, str], None]


class EquipmentModel:
    """
    Core business logic for equipment control.

    Manages instruments, state machine, and test execution.
    Does not know about the GUI.
    """

    def __init__(self, visa_connection: VISAConnection):
        """
        Initialize equipment model.

        Args:
            visa_connection: VISA connection manager
        """
        self._visa = visa_connection
        self._state_machine = StateMachine()
        self._instruments: dict[str, BaseInstrument] = {}
        self._test_plan: TestPlan | None = None
        self._stop_requested = False

        # Callbacks for test execution
        self._progress_callbacks: list[TestProgressCallback] = []
        self._complete_callbacks: list[TestCompleteCallback] = []

    @property
    def state(self) -> EquipmentState:
        """Get current equipment state."""
        return self._state_machine.state

    @property
    def test_plan(self) -> TestPlan | None:
        """Get loaded test plan."""
        return self._test_plan

    @property
    def instruments(self) -> dict[str, BaseInstrument]:
        """Get dictionary of instruments by name."""
        return self._instruments

    def register_state_callback(
        self, callback: Callable[[EquipmentState, EquipmentState], None]
    ) -> None:
        """Register callback for state changes."""
        self._state_machine.register_callback(callback)

    def register_progress_callback(self, callback: TestProgressCallback) -> None:
        """Register callback for test progress updates."""
        self._progress_callbacks.append(callback)

    def register_complete_callback(self, callback: TestCompleteCallback) -> None:
        """Register callback for test completion."""
        self._complete_callbacks.append(callback)

    def scan_resources(self) -> list[str]:
        """
        Scan for available VISA resources.

        Returns:
            List of resource address strings
        """
        if not self._visa.is_open:
            self._visa.open()
        return list(self._visa.list_resources())

    def add_instrument(self, name: str, resource_address: str, instrument_type: str, timeout_ms: int = 5000) -> None:
        """
        Add an instrument to the model.

        Args:
            name: Human-readable name
            resource_address: VISA address
            instrument_type: Type string (e.g., "power_supply")
            timeout_ms: Communication timeout
        """
        if instrument_type == "power_supply":
            instrument = PowerSupply(name, resource_address, timeout_ms)
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")

        self._instruments[name] = instrument
        logger.info("Added instrument: %s (%s) at %s", name, instrument_type, resource_address)

    def connect(self) -> None:
        """
        Connect to all configured instruments.

        Transitions to IDLE state on success, ERROR on failure.
        """
        if self._state_machine.state not in (EquipmentState.UNKNOWN, EquipmentState.ERROR):
            raise RuntimeError(f"Cannot connect in {self._state_machine.state.name} state")

        try:
            if not self._visa.is_open:
                self._visa.open()

            for name, instrument in self._instruments.items():
                if not instrument.is_connected:
                    resource = self._visa.open_resource(
                        instrument.resource_address,
                        instrument._timeout_ms,
                    )
                    instrument.connect(resource)

            self._state_machine.to_idle()
            logger.info("All instruments connected")

        except Exception as e:
            logger.error("Connection failed: %s", e)
            self._state_machine.to_error(str(e))
            raise

    def disconnect(self) -> None:
        """Disconnect from all instruments."""
        for name, instrument in self._instruments.items():
            if instrument.is_connected:
                instrument.disconnect()

        self._state_machine.reset()
        logger.info("All instruments disconnected")

    def load_test_plan(self, test_plan: TestPlan) -> None:
        """
        Load a test plan.

        Args:
            test_plan: TestPlan to load

        Raises:
            ValueError: If test plan is invalid
        """
        errors = test_plan.validate()
        if errors:
            raise ValueError(f"Invalid test plan: {'; '.join(errors)}")

        self._test_plan = test_plan
        logger.info("Loaded test plan: %s", test_plan)

    def run_test(self) -> None:
        """
        Execute the loaded test plan.

        Must be called from a background thread.
        Transitions through RUNNING state and back to IDLE on completion.
        """
        if self._test_plan is None:
            raise RuntimeError("No test plan loaded")

        if self._state_machine.state != EquipmentState.IDLE:
            raise RuntimeError(f"Cannot run test in {self._state_machine.state.name} state")

        self._stop_requested = False
        self._state_machine.to_running()

        try:
            self._execute_test_plan()
            success = not self._stop_requested
            message = "Test completed" if success else "Test stopped by user"
        except Exception as e:
            logger.error("Test execution failed: %s", e)
            self._state_machine.to_error(str(e))
            self._notify_complete(False, str(e))
            raise
        finally:
            if self._state_machine.state == EquipmentState.RUNNING:
                self._state_machine.to_idle()

        self._notify_complete(success, message)

    def stop_test(self) -> None:
        """Request test execution to stop."""
        if self._state_machine.state == EquipmentState.RUNNING:
            logger.info("Stop requested")
            self._stop_requested = True

    def _execute_test_plan(self) -> None:
        """Execute test plan steps."""
        if self._test_plan is None:
            return

        # Get the power supply (assuming single instrument for now)
        power_supply: PowerSupply | None = None
        for instrument in self._instruments.values():
            if isinstance(instrument, PowerSupply):
                power_supply = instrument
                break

        if power_supply is None:
            raise RuntimeError("No power supply connected")

        total_steps = self._test_plan.step_count
        sorted_steps = sorted(self._test_plan.steps, key=lambda s: s.step_number)

        for step in sorted_steps:
            if self._stop_requested:
                logger.info("Test stopped at step %d", step.step_number)
                break

            logger.info(
                "Executing step %d/%d: V=%.3f, I=%.3f",
                step.step_number,
                total_steps,
                step.voltage,
                step.current,
            )

            # Apply settings
            power_supply.set_voltage(step.voltage)
            power_supply.set_current(step.current)

            # Enable output on first step
            if step.step_number == 1:
                power_supply.enable_output()

            # Notify progress
            self._notify_progress(step.step_number, total_steps, step)

            # Wait for step duration
            if step.step_number < total_steps:
                next_step = sorted_steps[step.step_number]  # step_number is 1-based
                wait_time = next_step.time_seconds - step.time_seconds
                if wait_time > 0:
                    self._interruptible_sleep(wait_time)

        # Disable output at end
        if power_supply.is_connected:
            power_supply.disable_output()

    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep that can be interrupted by stop request."""
        end_time = time.time() + duration
        while time.time() < end_time and not self._stop_requested:
            time.sleep(min(0.1, end_time - time.time()))

    def _notify_progress(self, current: int, total: int, step: TestStep) -> None:
        """Notify progress callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(current, total, step)
            except Exception as e:
                logger.error("Error in progress callback: %s", e)

    def _notify_complete(self, success: bool, message: str) -> None:
        """Notify completion callbacks."""
        for callback in self._complete_callbacks:
            try:
                callback(success, message)
            except Exception as e:
                logger.error("Error in complete callback: %s", e)
