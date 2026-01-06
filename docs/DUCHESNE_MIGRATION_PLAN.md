# Duchesne: Strawberry GraphQL msgspec Migration Plan

This document outlines the detailed migration plan for transitioning Strawberry GraphQL's internal architecture from `dataclasses` to `msgspec`. The project is codenamed "Duchesne".

## Executive Summary

The migration involves replacing `dataclasses` with `msgspec.Struct` for internal type definitions while maintaining full backward compatibility with the public API. The key challenge is that `StrawberryField` directly inherits from `dataclasses.Field`, creating deep coupling that requires a strategic shim layer approach.

## Architecture Overview

### Current State
- `StrawberryField` inherits from `dataclasses.Field`
- Schema generation relies on `dataclasses.fields(cls)` for field iteration
- `dataclasses.MISSING` is used as a sentinel throughout
- Internal types (`ExecutionContext`, `Info`, `StrawberryObjectDefinition`, etc.) are dataclasses

### Target State
- `StrawberryField` inherits from a custom `StructFieldBase` class
- Unified field iteration via `get_fields()` compatibility function
- Custom `MISSING` sentinel that works with both systems during migration
- Internal types converted to msgspec Structs for performance

---

## Phase 1: Compatibility Foundation (No Behavior Change)

**Goal:** Create the compatibility layer that enables gradual migration without breaking existing functionality.

**Estimated Duration:** 3-4 days

### Milestone 1.1: Create Core Compatibility Module

**Files to Create:**
- `strawberry/compat/__init__.py`
- `strawberry/compat/struct_field.py`
- `strawberry/compat/introspection.py`

**Implementation:**

```python
# strawberry/compat/struct_field.py
class _MissingSentinel:
    """Singleton sentinel that works with both dataclasses and msgspec."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self): return "MISSING"
    def __bool__(self): return False

MISSING = _MissingSentinel()

class StructFieldBase:
    """Base class providing dataclasses.Field compatible interface."""
    __slots__ = (
        'name', 'type', 'default', 'default_factory',
        'repr', 'hash', 'init', 'compare', 'metadata', 'kw_only'
    )
    # ... implementation
```

```python
# strawberry/compat/introspection.py
def get_fields(cls: type) -> list:
    """Unified field extraction - works with both dataclasses and msgspec Structs."""
    # Check for msgspec Struct
    if hasattr(cls, '__struct_fields__'):
        return [_wrap_struct_field(name, info, cls) for name, info in ...]
    
    # Fallback to dataclasses
    if dataclasses.is_dataclass(cls):
        return list(dataclasses.fields(cls))
    
    raise TypeError(f"{cls} is neither a Struct nor dataclass")

def is_missing(value) -> bool:
    """Check if value represents 'missing' in either system."""
    return value is MISSING or value is dataclasses.MISSING or value is msgspec.UNSET

def is_dataclass_or_struct(cls) -> bool:
    """Check if cls is either a dataclass or msgspec Struct."""
    return dataclasses.is_dataclass(cls) or hasattr(cls, '__struct_fields__')
```

### Milestone 1.2: Add Compatibility Tests

**Files to Create:**
- `tests/compat/__init__.py`
- `tests/compat/test_struct_field.py`
- `tests/compat/test_introspection.py`

**Test Coverage:**
- `StructFieldBase` has all required attributes matching `dataclasses.Field`
- `MISSING` sentinel behaves correctly in comparisons
- `get_fields()` returns identical results for dataclasses
- `is_missing()` correctly identifies all missing sentinels

### Verification Criteria for Phase 1:
- [x] All existing tests pass (no behavior change)
- [x] New compatibility module tests pass
- [x] `StructFieldBase` can be instantiated with same parameters as `dataclasses.Field`
- [x] `get_fields()` returns equivalent results to `dataclasses.fields()` for existing types

**Phase 1 Status: COMPLETE** (2026-01-05)

---

## Phase 2: Low-Risk Internal Type Migrations

**Goal:** Migrate simple internal types to validate the compatibility layer works correctly.

**Estimated Duration:** 3-4 days

### Milestone 2.1: Migrate Node Types (Lowest Risk)

**Files to Modify:**
- `strawberry/types/nodes.py`

**Types to Migrate:**
- `SelectedField`
- `FragmentSpread`
- `InlineFragment`

These are simple data containers with no complex inheritance or special dataclass features.

**Before:**
```python
@dataclasses.dataclass
class SelectedField:
    name: str
    directives: Directives
    arguments: Arguments
    selections: list[Selection]
    alias: str | None = None
```

**After:**
```python
import msgspec

class SelectedField(msgspec.Struct):
    name: str
    directives: Directives
    arguments: Arguments
    selections: list[Selection]
    alias: str | None = None
```

### Milestone 2.2: Migrate GlobalID (Frozen Type)

**Files to Modify:**
- `strawberry/relay/types.py`

`GlobalID` uses `frozen=True, order=True` which msgspec Structs support natively.

**Before:**
```python
@dataclasses.dataclass(order=True, frozen=True)
class GlobalID:
    type_name: str
    node_id: str
```

**After:**
```python
class GlobalID(msgspec.Struct, frozen=True, order=True):
    type_name: str
    node_id: str
```

### Milestone 2.3: Migrate Enum/Scalar Definitions

**Metaclass Conflict Resolution:**

Types that inherit from `StrawberryType` (an ABC) cannot also inherit from `msgspec.Struct` due to metaclass conflicts. This was resolved by:

1. Creating `StrawberryTypeProtocol` - a runtime-checkable Protocol for structural typing
2. Creating `StrawberryTypeMixin` - provides default implementations for msgspec Structs
3. Keeping `StrawberryType` ABC for backward compatibility with existing container types

**Types migrated using the mixin approach:**
- `EnumValue` - msgspec.Struct
- `EnumValueDefinition` - msgspec.Struct
- `StrawberryEnumDefinition` - msgspec.Struct + StrawberryTypeMixin
- `ScalarDefinition` - msgspec.Struct + StrawberryTypeMixin

### Verification Criteria for Phase 2:
- [x] All existing tests pass
- [x] Migrated types work correctly in schema generation
- [x] `from_node()` class methods still work
- [x] `GlobalID` ordering and freezing behavior preserved
- [x] Enum serialization/deserialization works correctly
- [x] Scalar serialization/deserialization works correctly

**Phase 2 Status: COMPLETE** (2026-01-05)

**Types migrated to msgspec.Struct:**
- `SelectedField` (nodes.py)
- `FragmentSpread` (nodes.py)
- `InlineFragment` (nodes.py)
- `GlobalID` (relay/types.py)
- `EnumValue` (enum.py)
- `EnumValueDefinition` (enum.py)
- `StrawberryEnumDefinition` (enum.py) - with StrawberryTypeMixin
- `ScalarDefinition` (scalar.py) - with StrawberryTypeMixin

**New infrastructure added:**
- `StrawberryTypeProtocol` (base.py) - Protocol for structural typing
- `StrawberryTypeMixin` (base.py) - Mixin for msgspec Struct compatibility

---

## Phase 3: Core Field System Migration (High Risk)

**Goal:** Migrate `StrawberryField` to use `StructFieldBase` instead of inheriting from `dataclasses.Field`.

**Estimated Duration:** 4-5 days

### Milestone 3.1: Migrate StrawberryField

**Files to Modify:**
- `strawberry/types/field.py`

**Key Changes:**
1. Change inheritance from `dataclasses.Field` to `StructFieldBase`
2. Maintain all existing attributes and properties
3. Ensure `__copy__` method works correctly
4. Preserve the `type` property getter/setter pattern

**Before:**
```python
class StrawberryField(dataclasses.Field):
    def __init__(self, ..., default=dataclasses.MISSING, ...):
        super().__init__(default=default, ...)
```

**After:**
```python
from strawberry.compat.struct_field import StructFieldBase, MISSING

class StrawberryField(StructFieldBase):
    def __init__(self, ..., default=MISSING, ...):
        super().__init__(default=default, ...)
```

### Milestone 3.2: Update Type Resolver

**Files to Modify:**
- `strawberry/types/type_resolver.py`

**Key Changes:**
1. Replace `dataclasses.fields(cls)` with `get_fields(cls)`
2. Replace `dataclasses.MISSING` checks with `is_missing()`
3. Update `isinstance(field, StrawberryField)` checks if needed

**Before:**
```python
for field in dataclasses.fields(cls):
    if isinstance(field, StrawberryField):
        if field.default is not dataclasses.MISSING:
            ...
```

**After:**
```python
from strawberry.compat.introspection import get_fields, is_missing

for field in get_fields(cls):
    if isinstance(field, StrawberryField):
        if not is_missing(field.default):
            ...
```

### Milestone 3.3: Update Schema Converter

**Files to Modify:**
- `strawberry/schema/schema_converter.py`

**Key Changes:**
1. Replace `dataclasses.MISSING` checks with `is_missing()`
2. Update any field iteration patterns

### Verification Criteria for Phase 3:
- [ ] All existing tests pass
- [ ] Schema generation produces identical output
- [ ] Field defaults work correctly
- [ ] Field metadata preserved
- [ ] `@strawberry.field` decorator works as before
- [ ] Resolver argument handling unchanged

---

## Phase 4: Performance-Critical Type Migrations

**Goal:** Migrate types that are created on every request for performance benefits.

**Estimated Duration:** 3-4 days

### Milestone 4.1: Migrate ExecutionContext

**Files to Modify:**
- `strawberry/types/execution.py`

**Special Handling Required:**
- `InitVar` → Custom `__init__` with `__post_init__` pattern
- `field(default_factory=...)` → msgspec default factory syntax

**Before:**
```python
@dataclasses.dataclass
class ExecutionContext:
    query: str | None
    schema: Schema
    provided_operation_name: dataclasses.InitVar[str | None] = None
    parse_options: ParseOptions = dataclasses.field(default_factory=lambda: ParseOptions())
    
    def __post_init__(self, provided_operation_name: str | None) -> None:
        self._provided_operation_name = provided_operation_name
```

**After:**
```python
class ExecutionContext(msgspec.Struct):
    query: str | None
    schema: Schema
    context: Any = None
    variables: dict[str, Any] | None = None
    parse_options: ParseOptions = msgspec.field(default_factory=ParseOptions)
    # ... other fields
    
    # Handle InitVar equivalent via factory function or custom __init__
```

### Milestone 4.2: Migrate Info

**Files to Modify:**
- `strawberry/types/info.py`

**Special Handling Required:**
- Preserve `Generic[ContextType, RootValueType]` type parameters
- Maintain `__class_getitem__` override for single type parameter support

### Milestone 4.3: Migrate StrawberryObjectDefinition

**Files to Modify:**
- `strawberry/types/base.py`

**Special Handling Required:**
- `eq=False` → msgspec equivalent
- `field(default_factory=dict)` patterns
- `__post_init__` for Self annotation resolution

### Verification Criteria for Phase 4:
- [ ] All existing tests pass
- [ ] Performance benchmarks show improvement (or at least no regression)
- [ ] Generic type parameters work correctly
- [ ] `__post_init__` equivalent behavior preserved
- [ ] Memory usage reduced (msgspec uses `__slots__` by default)

---

## Phase 5: Decorator System Updates

**Goal:** Update the decorator system to work with msgspec Structs.

**Estimated Duration:** 3-4 days

### Milestone 5.1: Update Object Type Decorator

**Files to Modify:**
- `strawberry/types/object_type.py`

**Key Changes:**
1. Update `_wrap_dataclass()` to optionally create msgspec Structs
2. Update `__dataclass_fields__` access patterns
3. Ensure `@strawberry.type`, `@strawberry.input`, `@strawberry.interface` work

### Milestone 5.2: Update Config

**Files to Modify:**
- `strawberry/schema/config.py`

**Special Handling Required:**
- `InitVar` for `auto_camel_case` → alternative pattern

### Milestone 5.3: Update asdict Compatibility

**Files to Modify:**
- `strawberry/types/object_type.py` (asdict function)

**Key Changes:**
- Create compatibility wrapper for `dataclasses.asdict()` that works with msgspec Structs

```python
def asdict(obj: Any) -> dict[str, object]:
    """Convert a strawberry object into a dictionary."""
    if hasattr(obj, '__struct_fields__'):
        return msgspec.structs.asdict(obj)
    return dataclasses.asdict(obj)
```

### Verification Criteria for Phase 5:
- [ ] All existing tests pass
- [ ] `@strawberry.type` creates valid types
- [ ] `@strawberry.input` creates valid input types
- [ ] `@strawberry.interface` creates valid interfaces
- [ ] `strawberry.asdict()` works with both old and new types
- [ ] Schema string output unchanged

---

## Phase 6: Integration Points & Edge Cases

**Goal:** Handle integration points and edge cases.

**Estimated Duration:** 2-3 days

### Milestone 6.1: Pydantic Integration

**Files to Modify:**
- `strawberry/experimental/pydantic/fields.py`
- `strawberry/experimental/pydantic/object_type.py`

**Key Changes:**
- Update StrawberryField creation from Pydantic fields
- Ensure compatibility with both dataclass and msgspec backends

### Milestone 6.2: MyPy Plugin

**Files to Modify:**
- `strawberry/ext/mypy_plugin.py`

**Key Changes:**
- Add msgspec awareness to type transforms
- Ensure type checking works correctly

### Milestone 6.3: Directive System

**Files to Modify:**
- `strawberry/directive.py`
- `strawberry/schema_directive.py`

### Verification Criteria for Phase 6:
- [ ] Pydantic integration tests pass
- [ ] MyPy plugin works correctly
- [ ] Directive system unchanged
- [ ] All integration tests pass

---

## Phase 7: Cleanup & Optimization

**Goal:** Remove deprecated code paths and optimize.

**Estimated Duration:** 2-3 days

### Milestone 7.1: Remove Dataclass Fallbacks

Once all types are migrated and tests pass, remove fallback code paths that check for dataclasses.

### Milestone 7.2: Performance Benchmarking

Run comprehensive benchmarks comparing:
- Schema build time
- Request execution time
- Memory usage
- Field iteration performance

### Milestone 7.3: Documentation Updates

Update documentation to reflect internal changes (if any public API implications).

---

## Testing Strategy

### Parity Testing Harness

Create a test harness that validates identical behavior:

```python
# tests/compat/test_migration_parity.py
@pytest.mark.parametrize("backend", ["dataclass", "msgspec"])
def test_schema_generation_parity(backend):
    with migration_backend(backend):
        @strawberry.type
        class User:
            name: str
            age: int = 0
        
        schema = strawberry.Schema(query=Query)
        assert schema.as_str() == EXPECTED_SCHEMA

@pytest.mark.parametrize("backend", ["dataclass", "msgspec"])  
def test_field_metadata_preserved(backend):
    # Verify field.metadata access works identically
    ...
```

### Continuous Integration

Each milestone should:
1. Pass all existing tests
2. Pass new compatibility tests
3. Not change any public API behavior
4. Maintain schema output parity

---

## Risk Mitigation

### High-Risk Areas

1. **StrawberryField inheritance change** (Phase 3)
   - Mitigation: Extensive testing of field iteration patterns
   - Rollback: Keep dataclasses.Field as fallback

2. **InitVar handling** (Phase 4)
   - Mitigation: Create equivalent pattern with explicit __init__
   - Rollback: Keep dataclass for types using InitVar

3. **Generic type handling** (Phase 4)
   - Mitigation: Test all generic type combinations
   - Rollback: Keep Info as dataclass if issues arise

### Rollback Strategy

Each phase can be rolled back independently by:
1. Reverting the specific file changes
2. Keeping compatibility layer in place
3. Using feature flags if needed during transition

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Compatibility Foundation | 3-4 days | 3-4 days |
| Phase 2: Low-Risk Migrations | 3-4 days | 6-8 days |
| Phase 3: Core Field System | 4-5 days | 10-13 days |
| Phase 4: Performance Types | 3-4 days | 13-17 days |
| Phase 5: Decorator System | 3-4 days | 16-21 days |
| Phase 6: Integration Points | 2-3 days | 18-24 days |
| Phase 7: Cleanup & Optimization | 2-3 days | 20-27 days |

**Total Estimated Duration: 20-27 days**

---

## Success Criteria

1. All existing tests pass without modification
2. Schema output is byte-for-byte identical
3. Public API unchanged
4. Performance improved or unchanged
5. Memory usage reduced
6. No breaking changes for users

---

## Appendix: File Inventory

### Files Requiring Modification

| Priority | File | Changes |
|----------|------|---------|
| High | `strawberry/types/field.py` | Inherit from StructFieldBase |
| High | `strawberry/types/type_resolver.py` | Use get_fields() |
| High | `strawberry/types/object_type.py` | Update _wrap_dataclass() |
| Medium | `strawberry/types/execution.py` | Convert to Struct |
| Medium | `strawberry/types/info.py` | Convert to Struct |
| Medium | `strawberry/types/base.py` | Convert StrawberryObjectDefinition |
| Medium | `strawberry/types/nodes.py` | Convert node types |
| Medium | `strawberry/schema/schema_converter.py` | Update MISSING checks |
| Low | `strawberry/schema/config.py` | Convert StrawberryConfig |
| Low | `strawberry/types/enum.py` | Convert definitions |
| Low | `strawberry/types/scalar.py` | Convert ScalarDefinition |
| Low | `strawberry/relay/types.py` | Convert GlobalID |
| Low | `strawberry/directive.py` | Convert if needed |

### New Files to Create

| File | Purpose |
|------|---------|
| `strawberry/compat/__init__.py` | Compatibility module |
| `strawberry/compat/struct_field.py` | StructFieldBase, MISSING |
| `strawberry/compat/introspection.py` | get_fields(), is_missing() |
| `tests/compat/__init__.py` | Test module |
| `tests/compat/test_struct_field.py` | StructFieldBase tests |
| `tests/compat/test_introspection.py` | Introspection tests |
| `tests/compat/test_migration_parity.py` | Parity tests |
