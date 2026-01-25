"""Equipment model - core business logic."""

import logging
import time
from typing import Callable

from ..instruments import BaseInstrument, PowerSupply, SignalGenerator, VISAConnection
from .state_machine import EquipmentState, StateMachine
from .test_plan import (
    TestPlan,
    TestStep,
    PowerSupplyTestStep,
    SignalGeneratorTestStep,
    PLAN_TYPE_POWER_SUPPLY,
    PLAN_TYPE_SIGNAL_GENERATOR,
)

logger = logging.getLogger(__name__)

# Type aliases
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
        self._pause_requested = False
        self._time_remaining_in_step: float | None = None

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

    def get_instrument_identification(
        self, instrument_type: str
    ) -> tuple[str | None, str | None]:
        """
        Get model name and formatted identification for an instrument type.

        Args:
            instrument_type: Type of instrument ("power_supply" or "signal_generator")

        Returns:
            Tuple of (model_name, formatted_identification) or (None, None) if not found
        """
        for instrument in self._instruments.values():
            if instrument_type == "power_supply" and isinstance(
                instrument, PowerSupply
            ):
                if instrument.is_connected and instrument.identification:
                    return instrument.model(), instrument.formatted_identification()
            elif instrument_type == "signal_generator" and isinstance(
                instrument, SignalGenerator
            ):
                if instrument.is_connected and instrument.identification:
                    return instrument.model(), instrument.formatted_identification()
        return None, None

    def add_instrument(
        self,
        name: str,
        resource_address: str,
        instrument_type: str,
        timeout_ms: int = 5000,
        read_termination: str | None = "\n",
        write_termination: str | None = "\n",
    ) -> None:
        """
        Add an instrument to the model.

        Args:
            name: Human-readable name
            resource_address: VISA address
            instrument_type: Type string (e.g., "power_supply", "signal_generator")
            timeout_ms: Communication timeout
            read_termination: Character(s) appended to reads, or None for no termination
            write_termination: Character(s) appended to writes, or None for no termination
        """
        instrument: BaseInstrument
        if instrument_type == "power_supply":
            instrument = PowerSupply(
                name, resource_address, timeout_ms, read_termination, write_termination
            )
        elif instrument_type == "signal_generator":
            instrument = SignalGenerator(
                name, resource_address, timeout_ms, read_termination, write_termination
            )
        else:
            raise ValueError(f"Unknown instrument type: {instrument_type}")

        self._instruments[name] = instrument
        logger.info(
            "Added instrument: %s (%s) at %s", name, instrument_type, resource_address
        )

    def connect(self) -> None:
        """
        Connect to all configured instruments.

        Transitions to IDLE state on success, ERROR on failure.
        """
        if self._state_machine.state not in (
            EquipmentState.UNKNOWN,
            EquipmentState.ERROR,
        ):
            raise RuntimeError(
                f"Cannot connect in {self._state_machine.state.name} state"
            )

        try:
            if not self._visa.is_open:
                self._visa.open()

            for name, instrument in self._instruments.items():
                if not instrument.is_connected:
                    resource = self._visa.open_resource(
                        instrument.resource_address,
                        instrument._timeout_ms,
                        instrument._read_termination,
                        instrument._write_termination,
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
        if self._instruments.items() is None:
            logger.info("Attempted disconnect with no connected instruments")
        else:
            for name, instrument in self._instruments.items():
                if instrument.is_connected:
                    instrument.disconnect()
                else:
                    logger.info("%s is not connected. Unable to disconnect.", name)

            self._state_machine.reset()
            logger.info("All instruments disconnected")

        # TODO - review if this is necessary
        self._visa.close()

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
            raise RuntimeError(
                f"Cannot run test in {self._state_machine.state.name} state"
            )

        self._stop_requested = False
        self._pause_requested = False
        self._state_machine.to_running()

        try:
            # Dispatch based on plan type
            if self._test_plan.plan_type == PLAN_TYPE_POWER_SUPPLY:
                self._execute_power_supply_plan()
            elif self._test_plan.plan_type == PLAN_TYPE_SIGNAL_GENERATOR:
                self._execute_signal_generator_plan()
            else:
                raise RuntimeError(f"Unknown plan type: {self._test_plan.plan_type}")

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
        if self._state_machine.state in (
            EquipmentState.RUNNING,
            EquipmentState.PAUSED,
        ):
            logger.info("Stop requested")
            self._stop_requested = True
            self._pause_requested = False  # Clear pause flag so loop can exit

    def pause_test(self) -> None:
        """Request test execution to pause."""
        if self._state_machine.state == EquipmentState.RUNNING:
            logger.info("Pause requested")
            self._pause_requested = True

    def resume_test(self) -> None:
        """Request test execution to resume."""
        if self._state_machine.state == EquipmentState.PAUSED:
            logger.info("Resume requested")
            self._pause_requested = False

    def _execute_power_supply_plan(self) -> None:
        """Execute power supply test plan steps."""
        if (
            self._test_plan is None
            or self._test_plan.plan_type != PLAN_TYPE_POWER_SUPPLY
        ):
            return

        # Get the power supply
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

            # Type narrow: steps in power supply plan must be PowerSupplyTestStep
            if not isinstance(step, PowerSupplyTestStep):
                raise TypeError(f"Expected PowerSupplyTestStep, got {type(step)}")

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

    def _execute_signal_generator_plan(self) -> None:
        """Execute signal generator test plan steps."""
        if (
            self._test_plan is None
            or self._test_plan.plan_type != PLAN_TYPE_SIGNAL_GENERATOR
        ):
            return

        # Get the signal generator
        signal_gen: SignalGenerator | None = None
        for instrument in self._instruments.values():
            if isinstance(instrument, SignalGenerator):
                signal_gen = instrument
                break

        if signal_gen is None:
            raise RuntimeError("No signal generator connected")

        total_steps = self._test_plan.step_count
        sorted_steps = sorted(self._test_plan.steps, key=lambda s: s.step_number)

        for step in sorted_steps:
            if self._stop_requested:
                logger.info("Test stopped at step %d", step.step_number)
                break

            # Type narrow: steps in signal generator plan must be SignalGeneratorTestStep
            if not isinstance(step, SignalGeneratorTestStep):
                raise TypeError(f"Expected SignalGeneratorTestStep, got {type(step)}")

            logger.info(
                "Executing step %d/%d: F=%.1f Hz, P=%.2f dBm",
                step.step_number,
                total_steps,
                step.frequency,
                step.power,
            )

            # Apply settings
            signal_gen.set_frequency(step.frequency)
            signal_gen.set_power(step.power)

            # Enable output on first step
            if step.step_number == 1:
                signal_gen.enable_output()

            # Notify progress
            self._notify_progress(step.step_number, total_steps, step)

            # Wait for step duration
            if step.step_number < total_steps:
                next_step = sorted_steps[step.step_number]  # step_number is 1-based
                wait_time = next_step.time_seconds - step.time_seconds
                if wait_time > 0:
                    self._interruptible_sleep(wait_time)

        # Disable output at end
        if signal_gen.is_connected:
            signal_gen.disable_output()

    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep that can be interrupted by stop or pause request."""
        remaining = duration

        while remaining > 0 and not self._stop_requested:
            if self._pause_requested:
                # Store remaining time for this step
                self._time_remaining_in_step = remaining

                # Transition to PAUSED state
                self._state_machine.to_paused()

                # Wait until resumed or stopped
                while self._pause_requested and not self._stop_requested:
                    time.sleep(0.1)

                if not self._stop_requested:
                    # Resumed - continue with remaining time
                    remaining = self._time_remaining_in_step or remaining
                    self._time_remaining_in_step = None
                    self._state_machine.to_running()
            else:
                # Normal sleep chunk
                sleep_chunk = min(0.1, remaining)
                time.sleep(sleep_chunk)
                remaining -= sleep_chunk

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
