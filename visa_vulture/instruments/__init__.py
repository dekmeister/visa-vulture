"""VISA communication and instrument abstraction."""

from .visa_connection import VISAConnection
from .base_instrument import BaseInstrument
from .power_supply import PowerSupply
from .signal_generator import SignalGenerator
from .modulation import (
    ModulationType,
    ModulationConfig,
    AMModulationConfig,
    FMModulationConfig,
)
from .instrument_loader import (
    InstrumentEntry,
    scan_custom_instruments,
    build_instrument_catalog,
    create_instrument,
)

__all__ = [
    "VISAConnection",
    "BaseInstrument",
    "PowerSupply",
    "SignalGenerator",
    "ModulationType",
    "ModulationConfig",
    "AMModulationConfig",
    "FMModulationConfig",
    "InstrumentEntry",
    "scan_custom_instruments",
    "build_instrument_catalog",
    "create_instrument",
]
