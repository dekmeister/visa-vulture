"""Equipment state machine."""

import logging
from enum import Enum, auto
from typing import Callable

logger = logging.getLogger(__name__)


class EquipmentState(Enum):
    """Equipment state enumeration."""

    UNKNOWN = auto()  # Default startup state
    IDLE = auto()  # Connected and ready
    RUNNING = auto()  # Executing test plan
    PAUSED = auto()  # Test paused, can resume
    ERROR = auto()  # Failure occurred


# Valid state transitions
_VALID_TRANSITIONS: dict[EquipmentState, set[EquipmentState]] = {
    EquipmentState.UNKNOWN: {EquipmentState.IDLE, EquipmentState.ERROR},
    EquipmentState.IDLE: {
        EquipmentState.RUNNING,
        EquipmentState.ERROR,
        EquipmentState.UNKNOWN,
    },
    EquipmentState.RUNNING: {
        EquipmentState.IDLE,
        EquipmentState.PAUSED,
        EquipmentState.ERROR,
        EquipmentState.UNKNOWN,
    },
    EquipmentState.PAUSED: {
        EquipmentState.RUNNING,
        EquipmentState.IDLE,
        EquipmentState.ERROR,
        EquipmentState.UNKNOWN,
    },
    EquipmentState.ERROR: {EquipmentState.IDLE, EquipmentState.UNKNOWN},
}


StateChangeCallback = Callable[[EquipmentState, EquipmentState], None]


class StateMachine:
    """
    Manages equipment state and transitions.

    Validates transitions and notifies registered callbacks on state changes.
    """

    def __init__(self, initial_state: EquipmentState = EquipmentState.UNKNOWN):
        """
        Initialize state machine.

        Args:
            initial_state: Starting state (default UNKNOWN)
        """
        self._state = initial_state
        self._callbacks: list[StateChangeCallback] = []
        logger.info("State machine initialized in %s state", initial_state.name)

    @property
    def state(self) -> EquipmentState:
        """Get current state."""
        return self._state

    def can_transition_to(self, new_state: EquipmentState) -> bool:
        """
        Check if transition to new state is valid.

        Args:
            new_state: Target state

        Returns:
            True if transition is valid
        """
        return new_state in _VALID_TRANSITIONS.get(self._state, set())

    def transition_to(self, new_state: EquipmentState) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: Target state

        Returns:
            True if transition succeeded, False if invalid

        Raises:
            ValueError: If transition is not valid
        """
        if new_state == self._state:
            logger.debug("Already in %s state", new_state.name)
            return True

        if not self.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition: {self._state.name} -> {new_state.name}"
            )

        old_state = self._state
        self._state = new_state
        logger.info("State transition: %s -> %s", old_state.name, new_state.name)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                logger.error("Error in state change callback: %s", e)

        return True

    def register_callback(self, callback: StateChangeCallback) -> None:
        """
        Register a callback for state changes.

        Args:
            callback: Function called with (old_state, new_state) on transitions
        """
        self._callbacks.append(callback)
        logger.debug("Registered state change callback: %s", callback)

    def unregister_callback(self, callback: StateChangeCallback) -> None:
        """
        Unregister a state change callback.

        Args:
            callback: Previously registered callback function
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug("Unregistered state change callback: %s", callback)

    def to_error(self, reason: str = "") -> None:
        """
        Transition to ERROR state.

        Args:
            reason: Optional reason for the error
        """
        if reason:
            logger.error("Entering ERROR state: %s", reason)
        self.transition_to(EquipmentState.ERROR)

    def to_idle(self) -> None:
        """Transition to IDLE state."""
        self.transition_to(EquipmentState.IDLE)

    def to_running(self) -> None:
        """Transition to RUNNING state."""
        self.transition_to(EquipmentState.RUNNING)

    def to_paused(self) -> None:
        """Transition to PAUSED state."""
        self.transition_to(EquipmentState.PAUSED)

    def reset(self) -> None:
        """Reset to UNKNOWN state (for reconnection)."""
        self.transition_to(EquipmentState.UNKNOWN)
