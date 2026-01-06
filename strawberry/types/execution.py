from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    runtime_checkable,
)
from typing_extensions import Protocol, TypedDict, deprecated

import msgspec
from graphql import specified_rules

from strawberry.utils.operation import get_first_operation, get_operation_type

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing_extensions import NotRequired

    from graphql import ASTValidationRule
    from graphql.error.graphql_error import GraphQLError
    from graphql.language import DocumentNode, OperationDefinitionNode

    from strawberry.schema import Schema
    from strawberry.schema._graphql_core import GraphQLExecutionResult

    from .graphql import OperationType


class ExecutionContext(msgspec.Struct, kw_only=True):
    """Context for GraphQL execution.
    
    This struct holds all the information needed during GraphQL execution,
    including the query, schema, variables, and results.
    """
    query: str | None
    schema: Schema
    allowed_operations: tuple[OperationType, ...]
    context: Any = None
    variables: dict[str, Any] | None = None
    root_value: Any | None = None
    provided_operation_name: str | None = None
    graphql_document: DocumentNode | None = None
    pre_execution_errors: list[GraphQLError] | None = None
    result: GraphQLExecutionResult | None = None
    parse_options: ParseOptions | None = None
    validation_rules: tuple[type[ASTValidationRule], ...] | None = None
    extensions_results: dict[str, Any] | None = None
    operation_extensions: dict[str, Any] | None = None

    def get_parse_options(self) -> ParseOptions:
        """Get parse options, returning empty dict if not set."""
        return self.parse_options if self.parse_options is not None else ParseOptions()

    def get_validation_rules(self) -> tuple[type[ASTValidationRule], ...]:
        """Get validation rules, returning default rules if not set."""
        return self.validation_rules if self.validation_rules is not None else tuple(specified_rules)

    def get_extensions_results(self) -> dict[str, Any]:
        """Get extensions results, returning empty dict if not set."""
        return self.extensions_results if self.extensions_results is not None else {}

    @property
    def operation_name(self) -> str | None:
        if self.provided_operation_name is not None:
            return self.provided_operation_name

        definition = self._get_first_operation()
        if not definition:
            return None

        if not definition.name:
            return None

        return definition.name.value

    @property
    def operation_type(self) -> OperationType:
        graphql_document = self.graphql_document
        if not graphql_document:
            raise RuntimeError("No GraphQL document available")

        return get_operation_type(graphql_document, self.operation_name)

    def _get_first_operation(self) -> OperationDefinitionNode | None:
        graphql_document = self.graphql_document
        if not graphql_document:
            return None

        return get_first_operation(graphql_document)

    @property
    @deprecated("Use 'pre_execution_errors' instead")
    def errors(self) -> list[GraphQLError] | None:
        """Deprecated: Use pre_execution_errors instead."""
        return self.pre_execution_errors


class ExecutionResult(msgspec.Struct, kw_only=True):
    """Result of a GraphQL execution."""
    data: dict[str, Any] | None
    errors: list[GraphQLError] | None
    extensions: dict[str, Any] | None = None


class PreExecutionError(ExecutionResult):
    """Differentiate between a normal execution result and an immediate error.

    Immediate errors are errors that occur before the execution phase i.e validation errors,
    or any other error that occur before we interact with resolvers.

    These errors are required by `graphql-ws-transport` protocol in order to close the operation
    right away once the error is encountered.
    """


class ParseOptions(TypedDict):
    max_tokens: NotRequired[int]


@runtime_checkable
class SubscriptionExecutionResult(Protocol):
    def __aiter__(self) -> SubscriptionExecutionResult:  # pragma: no cover
        ...

    async def __anext__(self) -> Any:  # pragma: no cover
        ...


__all__ = [
    "ExecutionContext",
    "ExecutionResult",
    "ParseOptions",
    "SubscriptionExecutionResult",
]
