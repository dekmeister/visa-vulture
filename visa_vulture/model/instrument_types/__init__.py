"""Instrument-type subpackage: one module per type plus the generic framework.

A single registry (``INSTRUMENT_TYPE_REGISTRY``) drives generic test execution,
CSV parsing, soft-limit validation, and presentation. Each entry is an
``InstrumentTypeDescriptor`` bundling the instrument class, step dataclass,
declarative field specs, a per-run ``StepExecutor``, and a pure-data view spec.

New instrument types are added by writing a ``model/instrument_types/<type>.py``
module (constant, step dataclass, fields, executor, view spec, descriptor) and
adding its descriptor to ``_BUILTIN_DESCRIPTORS`` in ``registry.py``. Custom
instruments in the root ``instruments/`` directory cannot add new types; they
subclass built-ins.

This ``__init__`` re-exports the package's public surface so importers can keep
using ``from visa_vulture.model.instrument_types import ...``.
"""

from __future__ import annotations

from .descriptor import InstrumentTypeDescriptor, _check_descriptor_consistency
from .executor import MetadataParser, StepContext, StepExecutor
from .fields import (
    COMMON_COLUMNS,
    SoftLimitSpec,
    StepFieldSpec,
    default_columns,
    make_columns,
)
from .power_supply import (
    INSTRUMENT_TYPE_POWER_SUPPLY,
    PowerSupplyStepExecutor,
    PowerSupplyTestStep,
)
from .registry import INSTRUMENT_TYPE_REGISTRY, validate_soft_limit_config
from .signal_generator import (
    INSTRUMENT_TYPE_SIGNAL_GENERATOR,
    SignalGeneratorStepExecutor,
    SignalGeneratorTestStep,
    parse_signal_generator_metadata,
)

__all__ = [
    # framework
    "StepContext",
    "StepExecutor",
    "MetadataParser",
    "InstrumentTypeDescriptor",
    "_check_descriptor_consistency",
    "COMMON_COLUMNS",
    "SoftLimitSpec",
    "StepFieldSpec",
    "make_columns",
    "default_columns",
    # registry
    "INSTRUMENT_TYPE_REGISTRY",
    "validate_soft_limit_config",
    # power supply
    "INSTRUMENT_TYPE_POWER_SUPPLY",
    "PowerSupplyTestStep",
    "PowerSupplyStepExecutor",
    # signal generator
    "INSTRUMENT_TYPE_SIGNAL_GENERATOR",
    "SignalGeneratorTestStep",
    "SignalGeneratorStepExecutor",
    "parse_signal_generator_metadata",
]
