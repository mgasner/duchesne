"""Introspection utilities for dataclasses and msgspec Structs.

This module provides unified introspection functions that work with both
dataclasses and msgspec Structs, enabling gradual migration.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import msgspec

from strawberry.compat.struct_field import MISSING, StructFieldBase

if TYPE_CHECKING:
    from collections.abc import Sequence


class StructFieldWrapper(StructFieldBase):
    """Wrapper that presents msgspec struct field info as a StructFieldBase."""

    __slots__ = ("_struct_class",)

    def __init__(
        self,
        name: str,
        field_info: msgspec.structs.FieldInfo,
        struct_class: type,
    ) -> None:
        self._struct_class = struct_class
        
        default = MISSING
        default_factory = MISSING
        
        if field_info.default is not msgspec.UNSET:
            default = field_info.default
        if field_info.default_factory is not msgspec.UNSET:
            default_factory = field_info.default_factory

        super().__init__(
            default=default,
            default_factory=default_factory,
            repr=True,
            hash=None,
            init=True,
            compare=True,
            metadata={},
            kw_only=False,
        )
        self.name = name
        self._type = field_info.type


def get_fields(cls: type) -> Sequence[StructFieldBase | dataclasses.Field]:
    """Get fields from a dataclass or msgspec Struct.
    
    This function provides unified field extraction that works with both
    dataclasses and msgspec Structs, returning a consistent interface.
    
    Args:
        cls: A dataclass or msgspec Struct class
        
    Returns:
        A sequence of field objects (either dataclasses.Field or StructFieldBase)
        
    Raises:
        TypeError: If cls is neither a dataclass nor a msgspec Struct
    """
    if hasattr(cls, "__struct_fields__"):
        field_infos = msgspec.structs.fields(cls)
        return [
            StructFieldWrapper(fi.name, fi, cls)
            for fi in field_infos
        ]

    if dataclasses.is_dataclass(cls):
        return list(dataclasses.fields(cls))

    raise TypeError(f"{cls} is neither a msgspec Struct nor a dataclass")


def is_missing(value: Any) -> bool:
    """Check if a value represents 'missing' in any supported system.
    
    This function checks for:
    - Our custom MISSING sentinel
    - dataclasses.MISSING
    - msgspec.UNSET
    
    Args:
        value: The value to check
        
    Returns:
        True if the value represents "missing", False otherwise
    """
    return (
        value is MISSING
        or value is dataclasses.MISSING
        or value is msgspec.UNSET
    )


def is_dataclass_or_struct(cls: type) -> bool:
    """Check if a class is either a dataclass or msgspec Struct.
    
    Args:
        cls: The class to check
        
    Returns:
        True if cls is a dataclass or msgspec Struct, False otherwise
    """
    return dataclasses.is_dataclass(cls) or hasattr(cls, "__struct_fields__")


def is_struct(cls: type) -> bool:
    """Check if a class is a msgspec Struct.
    
    Args:
        cls: The class to check
        
    Returns:
        True if cls is a msgspec Struct, False otherwise
    """
    return hasattr(cls, "__struct_fields__")
