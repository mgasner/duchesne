from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

import msgspec

from strawberry.types.info import Info

from .name_converter import NameConverter

if TYPE_CHECKING:
    from collections.abc import Callable


class BatchingConfig(TypedDict):
    max_operations: int


class StrawberryConfig:
    """Configuration for a Strawberry schema."""
    
    __slots__ = (
        "auto_camel_case",
        "name_converter",
        "default_resolver",
        "relay_max_results",
        "relay_use_legacy_global_id",
        "disable_field_suggestions",
        "info_class",
        "enable_experimental_incremental_execution",
        "_unsafe_disable_same_type_validation",
        "batching_config",
    )

    def __init__(
        self,
        *,
        auto_camel_case: bool | None = None,
        name_converter: NameConverter | None = None,
        default_resolver: Callable[[Any, str], object] = getattr,
        relay_max_results: int = 100,
        relay_use_legacy_global_id: bool = False,
        disable_field_suggestions: bool = False,
        info_class: type[Info] = Info,
        enable_experimental_incremental_execution: bool = False,
        _unsafe_disable_same_type_validation: bool = False,
        batching_config: BatchingConfig | None = None,
    ) -> None:
        self.name_converter = name_converter if name_converter is not None else NameConverter()
        self.auto_camel_case = auto_camel_case
        self.default_resolver = default_resolver
        self.relay_max_results = relay_max_results
        self.relay_use_legacy_global_id = relay_use_legacy_global_id
        self.disable_field_suggestions = disable_field_suggestions
        self.info_class = info_class
        self.enable_experimental_incremental_execution = enable_experimental_incremental_execution
        self._unsafe_disable_same_type_validation = _unsafe_disable_same_type_validation
        self.batching_config = batching_config

        if auto_camel_case is not None:
            self.name_converter.auto_camel_case = auto_camel_case

        if not issubclass(self.info_class, Info):
            raise TypeError("`info_class` must be a subclass of strawberry.Info")


__all__ = ["StrawberryConfig"]
