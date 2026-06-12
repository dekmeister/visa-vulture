"""The ``InstrumentTypeDescriptor`` bundle and its import-time consistency check.

A descriptor is everything the program needs to support one instrument type;
generic parsing, validation, execution, and presentation all read from it.
"""

from __future__ import annotations

from dataclasses import dataclass, fields as dataclass_fields

from ...view_specs import InstrumentViewSpec
from ...instruments import BaseInstrument
from ..test_plan import TestStep
from .executor import MetadataParser, StepExecutor
from .fields import StepFieldSpec


@dataclass(frozen=True)
class InstrumentTypeDescriptor:
    """Everything the program needs to support one instrument type."""

    instrument_type: str  # "power_supply" — the single name for this concept
    display_name: str  # "Power Supply"
    instrument_cls: type[BaseInstrument]
    step_cls: type[TestStep]
    fields: tuple[StepFieldSpec, ...]
    executor_cls: type[StepExecutor]
    view: InstrumentViewSpec  # pure data (no Tkinter)
    parse_plan_metadata: MetadataParser | None = None


def _check_descriptor_consistency(descriptor: InstrumentTypeDescriptor) -> None:
    """Import-time guard: field-spec names must equal the step class's own fields.

    Compares ``{spec.name}`` against the step dataclass's own (non-inherited)
    fields — ``fields(step_cls)`` minus ``fields(TestStep)``. Catches a future
    session adding a step attribute without a field spec, or vice versa.
    """
    base_names = {f.name for f in dataclass_fields(TestStep)}
    own_names = {f.name for f in dataclass_fields(descriptor.step_cls)} - base_names
    spec_names = {spec.name for spec in descriptor.fields}
    if spec_names != own_names:
        raise ValueError(
            f"Descriptor for '{descriptor.instrument_type}': field specs "
            f"{sorted(spec_names)} do not match {descriptor.step_cls.__name__} "
            f"own fields {sorted(own_names)}"
        )
