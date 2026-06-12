"""The built-in descriptor list, the assembled ``INSTRUMENT_TYPE_REGISTRY``, and
the registry-aware soft-limit config validator.

Adding a new instrument type means writing a ``model/instrument_types/<type>.py``
module and adding its descriptor to ``_BUILTIN_DESCRIPTORS`` below — nothing else
in the generic framework changes.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping

from .descriptor import InstrumentTypeDescriptor, _check_descriptor_consistency
from .fields import SoftLimitSpec
from .power_supply import POWER_SUPPLY_DESCRIPTOR
from .signal_generator import SIGNAL_GENERATOR_DESCRIPTOR

if TYPE_CHECKING:
    from ...config.schema import ValidationLimits


_BUILTIN_DESCRIPTORS: tuple[InstrumentTypeDescriptor, ...] = (
    POWER_SUPPLY_DESCRIPTOR,
    SIGNAL_GENERATOR_DESCRIPTOR,
)


for _descriptor in _BUILTIN_DESCRIPTORS:
    _check_descriptor_consistency(_descriptor)


# Literal frozen mapping — no register()/mutation helpers. Custom instruments
# cannot add types; new types are added by editing _BUILTIN_DESCRIPTORS above.
INSTRUMENT_TYPE_REGISTRY: Mapping[str, InstrumentTypeDescriptor] = MappingProxyType(
    {d.instrument_type: d for d in _BUILTIN_DESCRIPTORS}
)


def validate_soft_limit_config(
    limits: "ValidationLimits",
    registry: Mapping[str, InstrumentTypeDescriptor] = INSTRUMENT_TYPE_REGISTRY,
) -> tuple[list[str], list[str]]:
    """Validate config-supplied instrument soft limits against the registry.

    The config layer only checks that limit values are numeric; per-key
    constraints (and the recipe for which sections/keys exist) live in the
    descriptors' ``SoftLimitSpec``s, so this registry-aware check runs at startup.

    Returns ``(errors, warnings)``:
      * errors — a config-supplied value violates its field's ``config_min``
        constraint (e.g. a negative frequency limit). These should block launch.
      * warnings — a section or key matching no descriptor field (e.g. the typo
        ``frequency_max_hzz``). These are logged but do not block launch; today
        such typos are silently ignored, which hides mistakes.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Build {section: {json_key: SoftLimitSpec}} from the registry.
    known: dict[str, dict[str, SoftLimitSpec]] = {}
    for instrument_type, descriptor in registry.items():
        keys: dict[str, SoftLimitSpec] = {}
        for fspec in descriptor.fields:
            soft = fspec.soft_limits
            if soft is None:
                continue
            if soft.min_key is not None:
                keys[soft.min_key] = soft
            if soft.max_key is not None:
                keys[soft.max_key] = soft
        known[instrument_type] = keys

    for section, values in limits.instrument_limits.items():
        section_keys = known.get(section)
        if section_keys is None:
            warnings.append(f"Unknown validation_limits section '{section}'")
            continue
        for key, value in values.items():
            soft = section_keys.get(key)
            if soft is None:
                warnings.append(
                    f"Unknown validation_limits key 'validation_limits.{section}.{key}'"
                )
                continue
            if soft.config_min is not None:
                op = ">" if soft.config_min_exclusive else ">="
                violated = (
                    value <= soft.config_min
                    if soft.config_min_exclusive
                    else value < soft.config_min
                )
                if violated:
                    errors.append(
                        f"validation_limits.{section}.{key} must be numeric "
                        f"{op} {soft.config_min:g}, got {value}"
                    )

    return errors, warnings
