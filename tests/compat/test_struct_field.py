"""Tests for StructFieldBase and MISSING sentinel."""

import dataclasses

import msgspec
import pytest

from strawberry.compat.struct_field import MISSING, StructFieldBase, is_missing_value


class TestMissingSentinel:
    def test_missing_is_singleton(self):
        from strawberry.compat.struct_field import _MissingSentinel

        instance1 = _MissingSentinel()
        instance2 = _MissingSentinel()
        assert instance1 is instance2
        assert instance1 is MISSING

    def test_missing_repr(self):
        assert repr(MISSING) == "MISSING"

    def test_missing_bool_is_false(self):
        assert not MISSING
        assert bool(MISSING) is False

    def test_missing_identity(self):
        assert MISSING is MISSING
        value = MISSING
        assert value is MISSING


class TestIsMissingValue:
    def test_our_missing(self):
        assert is_missing_value(MISSING) is True

    def test_dataclasses_missing(self):
        assert is_missing_value(dataclasses.MISSING) is True

    def test_msgspec_unset(self):
        assert is_missing_value(msgspec.UNSET) is True

    def test_none_is_not_missing(self):
        assert is_missing_value(None) is False

    def test_empty_string_is_not_missing(self):
        assert is_missing_value("") is False

    def test_zero_is_not_missing(self):
        assert is_missing_value(0) is False

    def test_false_is_not_missing(self):
        assert is_missing_value(False) is False


class TestStructFieldBase:
    def test_default_values(self):
        field = StructFieldBase()
        assert field.name == ""
        assert field.type is None
        assert field.default is MISSING
        assert field.default_factory is MISSING
        assert field.repr is True
        assert field.hash is None
        assert field.init is True
        assert field.compare is True
        assert field.metadata == {}
        assert field.kw_only is False

    def test_with_default(self):
        field = StructFieldBase(default="hello")
        assert field.default == "hello"
        assert field.default_factory is MISSING

    def test_with_default_factory(self):
        factory = list
        field = StructFieldBase(default_factory=factory)
        assert field.default is MISSING
        assert field.default_factory is factory

    def test_with_metadata(self):
        metadata = {"key": "value", "number": 42}
        field = StructFieldBase(metadata=metadata)
        assert field.metadata == metadata

    def test_name_assignment(self):
        field = StructFieldBase()
        field.name = "my_field"
        assert field.name == "my_field"

    def test_type_property(self):
        field = StructFieldBase()
        field.type = str
        assert field.type is str

    def test_repr(self):
        field = StructFieldBase(default="test")
        field.name = "my_field"
        field.type = str
        repr_str = repr(field)
        assert "StructFieldBase" in repr_str
        assert "my_field" in repr_str
        assert "test" in repr_str

    def test_equality_same_values(self):
        field1 = StructFieldBase(default="x", init=True, repr=True)
        field1.name = "test"
        field2 = StructFieldBase(default="x", init=True, repr=True)
        field2.name = "test"
        assert field1 == field2

    def test_equality_different_names(self):
        field1 = StructFieldBase(default="x")
        field1.name = "test1"
        field2 = StructFieldBase(default="x")
        field2.name = "test2"
        assert field1 != field2

    def test_equality_different_defaults(self):
        field1 = StructFieldBase(default="x")
        field1.name = "test"
        field2 = StructFieldBase(default="y")
        field2.name = "test"
        assert field1 != field2

    def test_hash(self):
        field = StructFieldBase(default="x")
        field.name = "test"
        h = hash(field)
        assert isinstance(h, int)

    def test_kw_only(self):
        field = StructFieldBase(kw_only=True)
        assert field.kw_only is True

    def test_init_false(self):
        field = StructFieldBase(init=False)
        assert field.init is False

    def test_compare_false(self):
        field = StructFieldBase(compare=False)
        assert field.compare is False

    def test_repr_false(self):
        field = StructFieldBase(repr=False)
        assert field.repr is False


class TestStructFieldBaseDataclassCompatibility:
    """Test that StructFieldBase has the same interface as dataclasses.Field."""

    def test_has_same_core_attributes(self):
        @dataclasses.dataclass
        class Sample:
            x: int = 0

        dc_field = dataclasses.fields(Sample)[0]
        struct_field = StructFieldBase(default=0)
        struct_field.name = "x"
        struct_field.type = int

        assert hasattr(struct_field, "name")
        assert hasattr(struct_field, "type")
        assert hasattr(struct_field, "default")
        assert hasattr(struct_field, "default_factory")
        assert hasattr(struct_field, "repr")
        assert hasattr(struct_field, "hash")
        assert hasattr(struct_field, "init")
        assert hasattr(struct_field, "compare")
        assert hasattr(struct_field, "metadata")
        assert hasattr(struct_field, "kw_only")

    def test_default_matches_dataclass_field(self):
        @dataclasses.dataclass
        class Sample:
            x: int = 42

        dc_field = dataclasses.fields(Sample)[0]
        struct_field = StructFieldBase(default=42)
        struct_field.name = "x"

        assert struct_field.name == dc_field.name
        assert struct_field.default == dc_field.default

    def test_default_factory_pattern(self):
        @dataclasses.dataclass
        class Sample:
            items: list = dataclasses.field(default_factory=list)

        dc_field = dataclasses.fields(Sample)[0]
        struct_field = StructFieldBase(default_factory=list)
        struct_field.name = "items"

        assert struct_field.name == dc_field.name
        assert struct_field.default_factory == dc_field.default_factory
