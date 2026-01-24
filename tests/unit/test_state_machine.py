"""Tests for the state machine module."""

import pytest

from src.model.state_machine import EquipmentState, StateMachine


class TestEquipmentState:
    """Tests for EquipmentState enum."""

    def test_state_values_exist(self) -> None:
        """Verify all four states exist."""
        assert EquipmentState.UNKNOWN is not None
        assert EquipmentState.IDLE is not None
        assert EquipmentState.RUNNING is not None
        assert EquipmentState.ERROR is not None

    def test_states_are_unique(self) -> None:
        """Verify each state has a unique value."""
        states = [
            EquipmentState.UNKNOWN,
            EquipmentState.IDLE,
            EquipmentState.RUNNING,
            EquipmentState.ERROR,
        ]
        values = [s.value for s in states]
        assert len(values) == len(set(values))


class TestStateMachineInitialization:
    """Tests for StateMachine initialization."""

    def test_initial_state_defaults_to_unknown(self) -> None:
        """Default state should be UNKNOWN."""
        sm = StateMachine()
        assert sm.state == EquipmentState.UNKNOWN

    def test_initial_state_can_be_customized(self) -> None:
        """Can pass custom initial state."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        assert sm.state == EquipmentState.IDLE

    def test_state_property_returns_current_state(self, state_machine: StateMachine) -> None:
        """state property returns the current state."""
        assert state_machine.state == EquipmentState.UNKNOWN


class TestCanTransitionTo:
    """Tests for can_transition_to method."""

    def test_can_transition_from_unknown_to_idle(self) -> None:
        """UNKNOWN -> IDLE is valid."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        assert sm.can_transition_to(EquipmentState.IDLE) is True

    def test_can_transition_from_unknown_to_error(self) -> None:
        """UNKNOWN -> ERROR is valid."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        assert sm.can_transition_to(EquipmentState.ERROR) is True

    def test_cannot_transition_from_unknown_to_running(self) -> None:
        """UNKNOWN -> RUNNING is invalid."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        assert sm.can_transition_to(EquipmentState.RUNNING) is False

    def test_can_transition_from_idle_to_running(self) -> None:
        """IDLE -> RUNNING is valid."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        assert sm.can_transition_to(EquipmentState.RUNNING) is True

    def test_can_transition_from_idle_to_error(self) -> None:
        """IDLE -> ERROR is valid."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        assert sm.can_transition_to(EquipmentState.ERROR) is True

    def test_can_transition_from_idle_to_unknown(self) -> None:
        """IDLE -> UNKNOWN is valid."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        assert sm.can_transition_to(EquipmentState.UNKNOWN) is True

    def test_can_transition_from_running_to_idle(self) -> None:
        """RUNNING -> IDLE is valid."""
        sm = StateMachine(initial_state=EquipmentState.RUNNING)
        assert sm.can_transition_to(EquipmentState.IDLE) is True

    def test_can_transition_from_running_to_error(self) -> None:
        """RUNNING -> ERROR is valid."""
        sm = StateMachine(initial_state=EquipmentState.RUNNING)
        assert sm.can_transition_to(EquipmentState.ERROR) is True

    def test_can_transition_from_running_to_unknown(self) -> None:
        """RUNNING -> UNKNOWN is valid."""
        sm = StateMachine(initial_state=EquipmentState.RUNNING)
        assert sm.can_transition_to(EquipmentState.UNKNOWN) is True

    def test_can_transition_from_error_to_idle(self) -> None:
        """ERROR -> IDLE is valid."""
        sm = StateMachine(initial_state=EquipmentState.ERROR)
        assert sm.can_transition_to(EquipmentState.IDLE) is True

    def test_can_transition_from_error_to_unknown(self) -> None:
        """ERROR -> UNKNOWN is valid."""
        sm = StateMachine(initial_state=EquipmentState.ERROR)
        assert sm.can_transition_to(EquipmentState.UNKNOWN) is True

    def test_cannot_transition_from_error_to_running(self) -> None:
        """ERROR -> RUNNING is invalid."""
        sm = StateMachine(initial_state=EquipmentState.ERROR)
        assert sm.can_transition_to(EquipmentState.RUNNING) is False


class TestTransitionTo:
    """Tests for transition_to method."""

    def test_transition_to_same_state_succeeds(self) -> None:
        """Transitioning to current state returns True without change."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        result = sm.transition_to(EquipmentState.IDLE)
        assert result is True
        assert sm.state == EquipmentState.IDLE

    def test_valid_transition_updates_state(self) -> None:
        """Valid transition changes state."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        result = sm.transition_to(EquipmentState.IDLE)
        assert result is True
        assert sm.state == EquipmentState.IDLE

    def test_invalid_transition_raises_value_error(self) -> None:
        """Invalid transition raises ValueError."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        with pytest.raises(ValueError, match="Invalid state transition"):
            sm.transition_to(EquipmentState.RUNNING)

    def test_invalid_transition_preserves_state(self) -> None:
        """State is unchanged after invalid transition attempt."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        try:
            sm.transition_to(EquipmentState.RUNNING)
        except ValueError:
            pass
        assert sm.state == EquipmentState.UNKNOWN


class TestCallbacks:
    """Tests for callback functionality."""

    def test_transition_notifies_callbacks(self) -> None:
        """State change triggers registered callbacks."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        callback_called = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            callback_called.append((old, new))

        sm.register_callback(callback)
        sm.transition_to(EquipmentState.IDLE)

        assert len(callback_called) == 1

    def test_callback_receives_old_and_new_state(self) -> None:
        """Callback receives (old_state, new_state) tuple."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        received_states = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            received_states.append((old, new))

        sm.register_callback(callback)
        sm.transition_to(EquipmentState.IDLE)

        assert received_states[0] == (EquipmentState.UNKNOWN, EquipmentState.IDLE)

    def test_callback_not_called_for_same_state_transition(self) -> None:
        """Callback is not called when transitioning to same state."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        callback_count = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            callback_count.append(1)

        sm.register_callback(callback)
        sm.transition_to(EquipmentState.IDLE)

        assert len(callback_count) == 0

    def test_callback_error_is_logged_not_raised(self) -> None:
        """Exception in callback is logged, not propagated."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)

        def bad_callback(old: EquipmentState, new: EquipmentState) -> None:
            raise RuntimeError("Callback error")

        sm.register_callback(bad_callback)

        # Should not raise
        sm.transition_to(EquipmentState.IDLE)
        assert sm.state == EquipmentState.IDLE

    def test_multiple_callbacks_all_called(self) -> None:
        """All registered callbacks are called."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        calls = []

        def callback1(old: EquipmentState, new: EquipmentState) -> None:
            calls.append("cb1")

        def callback2(old: EquipmentState, new: EquipmentState) -> None:
            calls.append("cb2")

        sm.register_callback(callback1)
        sm.register_callback(callback2)
        sm.transition_to(EquipmentState.IDLE)

        assert "cb1" in calls
        assert "cb2" in calls


class TestCallbackRegistration:
    """Tests for callback registration and unregistration."""

    def test_register_callback(self) -> None:
        """register_callback adds callback to list."""
        sm = StateMachine()
        callbacks_called = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            callbacks_called.append(1)

        sm.register_callback(callback)
        sm.transition_to(EquipmentState.IDLE)

        assert len(callbacks_called) == 1

    def test_unregister_callback(self) -> None:
        """unregister_callback removes callback."""
        sm = StateMachine()
        callbacks_called = []

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            callbacks_called.append(1)

        sm.register_callback(callback)
        sm.unregister_callback(callback)
        sm.transition_to(EquipmentState.IDLE)

        assert len(callbacks_called) == 0

    def test_unregister_nonexistent_callback_is_safe(self) -> None:
        """Unregistering missing callback does not raise."""
        sm = StateMachine()

        def callback(old: EquipmentState, new: EquipmentState) -> None:
            pass

        # Should not raise
        sm.unregister_callback(callback)


class TestConvenienceMethods:
    """Tests for convenience transition methods."""

    def test_to_error_transitions_to_error_state(self) -> None:
        """to_error() transitions to ERROR state."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        sm.to_error()
        assert sm.state == EquipmentState.ERROR

    def test_to_error_with_reason_still_transitions(self) -> None:
        """to_error() with reason string still transitions."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        sm.to_error(reason="Something went wrong")
        assert sm.state == EquipmentState.ERROR

    def test_to_idle_transitions_to_idle_state(self) -> None:
        """to_idle() transitions to IDLE state."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        sm.to_idle()
        assert sm.state == EquipmentState.IDLE

    def test_to_running_transitions_to_running_state(self) -> None:
        """to_running() transitions to RUNNING state."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        sm.to_running()
        assert sm.state == EquipmentState.RUNNING

    def test_reset_transitions_to_unknown_state(self) -> None:
        """reset() transitions to UNKNOWN state."""
        sm = StateMachine(initial_state=EquipmentState.IDLE)
        sm.reset()
        assert sm.state == EquipmentState.UNKNOWN

    def test_convenience_methods_respect_valid_transitions(self) -> None:
        """Convenience methods still validate transitions."""
        sm = StateMachine(initial_state=EquipmentState.UNKNOWN)
        with pytest.raises(ValueError):
            sm.to_running()  # UNKNOWN -> RUNNING is invalid
