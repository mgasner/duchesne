"""Tests for introspection utilities."""

import dataclasses

import msgspec
import pytest

from strawberry.compat.introspection import (
    get_fields,
    is_dataclass_or_struct,
    is_missing,
    is_struct,
)
from strawberry.compat.struct_field import MISSING, StructFieldBase


class TestIsMissing:
    def test_our_missing(self):
        assert is_missing(MISSING) is True

    def test_dataclasses_missing(self):
        assert is_missing(dataclasses.MISSING) is True

    def test_msgspec_unset(self):
        assert is_missing(msgspec.UNSET) is True

    def test_none_is_not_missing(self):
        assert is_missing(None) is False

    def test_regular_values_not_missing(self):
        assert is_missing(0) is False
        assert is_missing("") is False
        assert is_missing([]) is False
        assert is_missing({}) is False


class TestIsDataclassOrStruct:
    def test_dataclass(self):
        @dataclasses.dataclass
        class MyDataclass:
            x: int

        assert is_dataclass_or_struct(MyDataclass) is True

    def test_struct(self):
        class MyStruct(msgspec.Struct):
            x: int

        assert is_dataclass_or_struct(MyStruct) is True

    def test_regular_class(self):
        class RegularClass:
            x: int

        assert is_dataclass_or_struct(RegularClass) is False

    def test_builtin_types(self):
        assert is_dataclass_or_struct(int) is False
        assert is_dataclass_or_struct(str) is False
        assert is_dataclass_or_struct(list) is False


class TestIsStruct:
    def test_struct(self):
        class MyStruct(msgspec.Struct):
            x: int

        assert is_struct(MyStruct) is True

    def test_dataclass_is_not_struct(self):
        @dataclasses.dataclass
        class MyDataclass:
            x: int

        assert is_struct(MyDataclass) is False

    def test_regular_class(self):
        class RegularClass:
            x: int

        assert is_struct(RegularClass) is False


class TestGetFieldsDataclass:
    def test_simple_dataclass(self):
        @dataclasses.dataclass
        class Simple:
            x: int
            y: str

        fields = get_fields(Simple)
        assert len(fields) == 2
        assert fields[0].name == "x"
        assert fields[1].name == "y"

    def test_dataclass_with_defaults(self):
        @dataclasses.dataclass
        class WithDefaults:
            x: int = 10
            y: str = "hello"

        fields = get_fields(WithDefaults)
        assert len(fields) == 2
        assert fields[0].default == 10
        assert fields[1].default == "hello"

    def test_dataclass_with_default_factory(self):
        @dataclasses.dataclass
        class WithFactory:
            items: list = dataclasses.field(default_factory=list)

        fields = get_fields(WithFactory)
        assert len(fields) == 1
        assert fields[0].default_factory is list

    def test_dataclass_returns_dataclass_fields(self):
        @dataclasses.dataclass
        class Sample:
            x: int

        fields = get_fields(Sample)
        assert isinstance(fields[0], dataclasses.Field)


class TestGetFieldsStruct:
    def test_simple_struct(self):
        class Simple(msgspec.Struct):
            x: int
            y: str

        fields = get_fields(Simple)
        assert len(fields) == 2
        assert fields[0].name == "x"
        assert fields[1].name == "y"

    def test_struct_with_defaults(self):
        class WithDefaults(msgspec.Struct):
            x: int = 10
            y: str = "hello"

        fields = get_fields(WithDefaults)
        assert len(fields) == 2
        assert fields[0].default == 10
        assert fields[1].default == "hello"

    def test_struct_with_default_factory(self):
        class WithFactory(msgspec.Struct):
            items: list = msgspec.field(default_factory=list)

        fields = get_fields(WithFactory)
        assert len(fields) == 1
        assert fields[0].default_factory is list

    def test_struct_returns_struct_field_base(self):
        class Sample(msgspec.Struct):
            x: int

        fields = get_fields(Sample)
        assert isinstance(fields[0], StructFieldBase)

    def test_struct_field_has_type(self):
        class Sample(msgspec.Struct):
            x: int
            y: str

        fields = get_fields(Sample)
        assert fields[0].type is int
        assert fields[1].type is str


class TestGetFieldsErrors:
    def test_regular_class_raises(self):
        class RegularClass:
            x: int

        with pytest.raises(TypeError, match="neither a msgspec Struct nor a dataclass"):
            get_fields(RegularClass)

    def test_builtin_raises(self):
        with pytest.raises(TypeError):
            get_fields(int)


class TestGetFieldsParity:
    """Test that get_fields returns equivalent results for dataclasses."""

    def test_field_count_matches(self):
        @dataclasses.dataclass
        class Sample:
            a: int
            b: str
            c: float

        dc_fields = dataclasses.fields(Sample)
        compat_fields = get_fields(Sample)
        assert len(dc_fields) == len(compat_fields)

    def test_field_names_match(self):
        @dataclasses.dataclass
        class Sample:
            first: int
            second: str

        dc_fields = dataclasses.fields(Sample)
        compat_fields = get_fields(Sample)
        assert [f.name for f in dc_fields] == [f.name for f in compat_fields]

    def test_field_defaults_match(self):
        @dataclasses.dataclass
        class Sample:
            x: int = 42
            y: str = "test"

        dc_fields = dataclasses.fields(Sample)
        compat_fields = get_fields(Sample)
        assert dc_fields[0].default == compat_fields[0].default
        assert dc_fields[1].default == compat_fields[1].default

    def test_field_types_match(self):
        @dataclasses.dataclass
        class Sample:
            x: int
            y: str

        dc_fields = dataclasses.fields(Sample)
        compat_fields = get_fields(Sample)
        assert dc_fields[0].type == compat_fields[0].type
        assert dc_fields[1].type == compat_fields[1].type
