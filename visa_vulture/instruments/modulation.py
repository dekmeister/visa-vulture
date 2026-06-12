"""Modulation configuration types for signal generators.

These parameterise the signal generator driver (``configure_modulation`` /
``set_modulation_enabled``), so they live driver-side in ``instruments/`` rather
than in the model. Stdlib-only neutral leaf.
"""

from dataclasses import dataclass
from enum import Enum


class ModulationType(Enum):
    """Supported modulation types for signal generators."""

    NONE = "none"
    AM = "am"
    FM = "fm"
    # Future: PSK = "psk", QAM = "qam", etc.


@dataclass
class ModulationConfig:
    """Base configuration for modulation.

    This is the base class for modulation configurations.
    Subclasses define specific parameters for each modulation type.
    """

    modulation_type: ModulationType
    modulation_frequency: float  # Hz - frequency of modulating signal

    def __post_init__(self) -> None:
        """Validate common modulation values."""
        if self.modulation_frequency <= 0:
            raise ValueError(
                f"modulation_frequency must be > 0, got {self.modulation_frequency}"
            )


@dataclass
class AMModulationConfig(ModulationConfig):
    """AM-specific modulation configuration."""

    depth: float = 50.0  # Percentage (0-100%)

    def __post_init__(self) -> None:
        """Validate AM modulation values."""
        super().__post_init__()
        if not 0 <= self.depth <= 100:
            raise ValueError(f"AM depth must be 0-100%, got {self.depth}")


@dataclass
class FMModulationConfig(ModulationConfig):
    """FM-specific modulation configuration."""

    deviation: float = 1000.0  # Hz

    def __post_init__(self) -> None:
        """Validate FM modulation values."""
        super().__post_init__()
        if self.deviation <= 0:
            raise ValueError(f"FM deviation must be > 0, got {self.deviation}")
