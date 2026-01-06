"""StructFieldBase and MISSING sentinel for dataclasses compatibility.

This module provides a base class that mimics dataclasses.Field interface
while being compatible with msgspec Structs.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

import msgspec

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping


class _MissingSentinel:
    """Singleton sentinel that works with both dataclasses and msgspec.
    
    This sentinel is used to represent "no value provided" in a way that
    is compatible with both dataclasses.MISSING and msgspec.UNSET.
    """

    _instance: _MissingSentinel | None = None

    def __new__(cls) -> _MissingSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "MISSING"

    def __bool__(self) -> bool:
        return False

    def __reduce__(self) -> str:
        return "MISSING"


MISSING = _MissingSentinel()


class StructFieldBase:
    """Base class providing dataclasses.Field compatible interface.
    
    This class provides the same interface as dataclasses.Field but can be
    used independently of the dataclasses machinery. It serves as the base
    for StrawberryField during the migration from dataclasses to msgspec.
    
    Attributes match dataclasses.Field for compatibility:
    - name: The name of the field
    - type: The type annotation of the field
    - default: The default value (MISSING if none)
    - default_factory: A callable that returns the default value
    - repr: Whether to include in __repr__
    - hash: Whether to include in __hash__
    - init: Whether to include in __init__
    - compare: Whether to include in comparison methods
    - metadata: Additional metadata mapping
    - kw_only: Whether the field is keyword-only
    """

    __slots__ = (
        "name",
        "_type",
        "default",
        "default_factory",
        "repr",
        "hash",
        "init",
        "compare",
        "metadata",
        "kw_only",
    )

    def __init__(
        self,
        *,
        default: Any = MISSING,
        default_factory: Callable[[], Any] | object = MISSING,
        repr: bool = True,
        hash: bool | None = None,
        init: bool = True,
        compare: bool = True,
        metadata: Mapping[Any, Any] | None = None,
        kw_only: bool = False,
    ) -> None:
        self.name: str = ""
        self._type: Any = None
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.hash = hash
        self.init = init
        self.compare = compare
        self.metadata = metadata if metadata is not None else {}
        self.kw_only = kw_only

    @property
    def type(self) -> Any:
        """The type annotation of the field."""
        return self._type

    @type.setter
    def type(self, value: Any) -> None:
        self._type = value

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"type={self.type!r}, "
            f"default={self.default!r}, "
            f"default_factory={self.default_factory!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (StructFieldBase, dataclasses.Field)):
            return NotImplemented
        return (
            self.name == other.name
            and self.default == other.default
            and self.default_factory == other.default_factory
            and self.repr == other.repr
            and self.init == other.init
            and self.compare == other.compare
            and self.kw_only == other.kw_only
        )

    def __hash__(self) -> int:
        return hash((self.name, self.default, self.repr, self.init, self.compare))


def is_missing_value(value: Any) -> bool:
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
