"""Compatibility layer for dataclasses to msgspec migration.

This module provides utilities that enable gradual migration from dataclasses
to msgspec Structs while maintaining backward compatibility.
"""

from strawberry.compat.introspection import (
    get_fields,
    is_dataclass_or_struct,
    is_missing,
)
from strawberry.compat.struct_field import MISSING, StructFieldBase

__all__ = [
    "MISSING",
    "StructFieldBase",
    "get_fields",
    "is_dataclass_or_struct",
    "is_missing",
]
