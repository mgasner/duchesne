"""Duchesne Migration Baseline Benchmarks.

These benchmarks establish baseline performance metrics for the dataclasses-based
implementation before migrating to msgspec. They focus on:

1. Type creation - Creating large numbers of Strawberry types
2. Schema building - Building schemas with many types and large unions
3. Field resolution - Resolving deeply nested queries (10 levels)
4. Large result sets - Queries returning ~1000 objects
5. Types with many fields - Schemas with ~1000 fields total

Run with: pytest tests/benchmarks/test_duchesne_baseline.py -v
Manual run: python tests/benchmarks/test_duchesne_baseline.py
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import time
from typing import TYPE_CHECKING, Annotated, Generic, TypeVar

import pytest

import strawberry
from strawberry.types.base import StrawberryObjectDefinition

if TYPE_CHECKING:
    from pytest_codspeed.plugin import BenchmarkFixture


T = TypeVar("T")


class TimingResult:
    def __init__(self, name: str):
        self.name = name
        self.start_time: float = 0
        self.end_time: float = 0
        self.iterations: int = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    @property
    def per_iteration_us(self) -> float:
        if self.iterations == 0:
            return 0
        return (self.end_time - self.start_time) * 1_000_000 / self.iterations


def create_type_with_n_fields(name: str, n: int):
    """Dynamically create a strawberry type with n fields."""
    annotations = {f"field_{i:03d}": str for i in range(n)}
    defaults = {f"field_{i:03d}": f"value_{i}" for i in range(n)}
    cls = type(name, (), {"__annotations__": annotations, **defaults})
    return strawberry.type(cls)


def create_union_type(name: str, members: list):
    """Create a union type from a list of member types."""
    if len(members) < 2:
        raise ValueError("Union requires at least 2 members")
    union_expr = functools.reduce(lambda a, b: a | b, members)
    return Annotated[union_expr, strawberry.union(name=name)]


@pytest.mark.benchmark
class TestTypeCreationBenchmarks:
    """Benchmarks for creating Strawberry types."""

    def test_create_simple_types_100(self, benchmark: BenchmarkFixture):
        """Benchmark creating 100 simple types with basic fields."""

        def run():
            types = []
            for i in range(100):
                @strawberry.type
                class DynamicType:
                    id: int
                    name: str
                    value: float
                    active: bool

                DynamicType.__name__ = f"SimpleType{i}"
                DynamicType.__qualname__ = f"SimpleType{i}"
                types.append(DynamicType)
            return types

        benchmark(run)

    def test_create_types_with_50_fields(self, benchmark: BenchmarkFixture):
        """Benchmark creating types with 50 fields each."""

        def run():
            types = []
            for i in range(20):
                t = create_type_with_n_fields(f"Type50Fields_{i}", 50)
                types.append(t)
            return types

        benchmark(run)

    def test_create_types_with_100_fields(self, benchmark: BenchmarkFixture):
        """Benchmark creating types with 100 fields each."""

        def run():
            types = []
            for i in range(10):
                t = create_type_with_n_fields(f"Type100Fields_{i}", 100)
                types.append(t)
            return types

        benchmark(run)

    def test_create_types_with_resolvers(self, benchmark: BenchmarkFixture):
        """Benchmark creating types with resolver methods."""

        def run():
            types = []
            for i in range(50):
                @strawberry.type
                class TypeWithResolvers:
                    id: int

                    @strawberry.field
                    def computed_a(self) -> str:
                        return f"computed_a_{self.id}"

                    @strawberry.field
                    def computed_b(self) -> int:
                        return self.id * 2

                    @strawberry.field
                    def computed_c(self) -> list[str]:
                        return [f"item_{j}" for j in range(5)]

                    @strawberry.field
                    def computed_d(self, multiplier: int = 1) -> int:
                        return self.id * multiplier

                TypeWithResolvers.__name__ = f"TypeWithResolvers{i}"
                TypeWithResolvers.__qualname__ = f"TypeWithResolvers{i}"
                types.append(TypeWithResolvers)
            return types

        benchmark(run)

    def test_create_input_types_100(self, benchmark: BenchmarkFixture):
        """Benchmark creating 100 input types."""

        def run():
            types = []
            for i in range(100):
                @strawberry.input
                class InputType:
                    field_a: str
                    field_b: int
                    field_c: float | None = None
                    field_d: bool = False

                InputType.__name__ = f"InputType{i}"
                InputType.__qualname__ = f"InputType{i}"
                types.append(InputType)
            return types

        benchmark(run)

    def test_create_interface_implementations_100(self, benchmark: BenchmarkFixture):
        """Benchmark creating 100 interface implementations."""

        @strawberry.interface
        class BaseInterface:
            id: strawberry.ID
            name: str

        def run():
            types = []
            for i in range(100):
                @strawberry.type
                class Implementation(BaseInterface):
                    id: strawberry.ID
                    name: str
                    extra_field: str = "extra"

                Implementation.__name__ = f"Implementation{i}"
                Implementation.__qualname__ = f"Implementation{i}"
                types.append(Implementation)
            return types

        benchmark(run)


@pytest.mark.benchmark
class TestLargeUnionBenchmarks:
    """Benchmarks for schemas with large unions (~100 members)."""

    def test_create_union_100_members(self, benchmark: BenchmarkFixture):
        """Benchmark creating a union with 100 member types."""

        def run():
            members = []
            for i in range(100):
                @strawberry.type
                class UnionMember:
                    id: int
                    type_id: int = i

                UnionMember.__name__ = f"UnionMember{i}"
                UnionMember.__qualname__ = f"UnionMember{i}"
                members.append(UnionMember)
            return members

        benchmark(run)

    def test_build_schema_union_100_members(self, benchmark: BenchmarkFixture):
        """Benchmark building a schema with a 100-member union."""
        members = []
        for i in range(100):
            @strawberry.type
            class UnionMember:
                id: int
                type_id: int = i
                name: str = "member"

            UnionMember.__name__ = f"LargeUnionMember{i}"
            UnionMember.__qualname__ = f"LargeUnionMember{i}"
            members.append(UnionMember)

        LargeUnion = create_union_type("LargeUnion", members)

        @strawberry.type
        class Query:
            @strawberry.field
            def search(self) -> list[LargeUnion]:
                return []

        def run():
            return strawberry.Schema(query=Query, types=members)

        benchmark(run)

    def test_resolve_union_100_members(self, benchmark: BenchmarkFixture):
        """Benchmark resolving a query against a 100-member union."""
        members = []
        for i in range(100):
            @strawberry.type
            class UnionMember:
                id: int
                type_id: int = i
                name: str = "member"

            UnionMember.__name__ = f"ResolveUnionMember{i}"
            UnionMember.__qualname__ = f"ResolveUnionMember{i}"
            members.append(UnionMember)

        ResolveUnion = create_union_type("ResolveUnion", members)

        @strawberry.type
        class Query:
            @strawberry.field
            def search(self) -> list[ResolveUnion]:
                return [members[i % 100](id=i) for i in range(1000)]

        schema = strawberry.Schema(query=Query, types=members)

        fragments = "\n".join(
            f"... on ResolveUnionMember{i} {{ id name }}" for i in range(100)
        )
        query = f"""
            query {{
                search {{
                    {fragments}
                }}
            }}
        """

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors


@pytest.mark.benchmark
class TestLargeFieldCountBenchmarks:
    """Benchmarks for schemas with ~1000 fields total."""

    def test_build_schema_1000_fields_single_type(self, benchmark: BenchmarkFixture):
        """Benchmark building a schema with a single type having 1000 fields."""
        LargeType = create_type_with_n_fields("TypeWith1000Fields", 1000)

        @strawberry.type
        class Query:
            @strawberry.field
            def large_type(self) -> LargeType:
                return LargeType()

        def run():
            return strawberry.Schema(query=Query)

        benchmark(run)

    def test_build_schema_1000_fields_distributed(self, benchmark: BenchmarkFixture):
        """Benchmark building a schema with 1000 fields across 20 types (50 each)."""
        types = [create_type_with_n_fields(f"DistType{i}", 50) for i in range(20)]

        @strawberry.type
        class Query:
            @strawberry.field
            def type_0(self) -> types[0]:
                return types[0]()

            @strawberry.field
            def type_1(self) -> types[1]:
                return types[1]()

            @strawberry.field
            def type_2(self) -> types[2]:
                return types[2]()

        def run():
            return strawberry.Schema(query=Query, types=types)

        benchmark(run)

    def test_resolve_type_with_100_fields(self, benchmark: BenchmarkFixture):
        """Benchmark resolving a query selecting 100 fields."""
        Type100 = create_type_with_n_fields("Resolve100Fields", 100)

        @strawberry.type
        class Query:
            @strawberry.field
            def items(self) -> list[Type100]:
                return [Type100() for _ in range(100)]

        schema = strawberry.Schema(query=Query)

        fields = " ".join(f"field_{i:03d}" for i in range(100))
        query = f"query {{ items {{ {fields} }} }}"

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors


@pytest.mark.benchmark
class TestDeepNestingBenchmarks:
    """Benchmarks for deeply nested queries (10 levels)."""

    def test_build_schema_10_levels_deep(self, benchmark: BenchmarkFixture):
        """Benchmark building a schema with 10 levels of nesting."""

        @strawberry.type
        class Level10:
            id: int
            name: str

        @strawberry.type
        class Level9:
            id: int
            children: list[Level10]

        @strawberry.type
        class Level8:
            id: int
            children: list[Level9]

        @strawberry.type
        class Level7:
            id: int
            children: list[Level8]

        @strawberry.type
        class Level6:
            id: int
            children: list[Level7]

        @strawberry.type
        class Level5:
            id: int
            children: list[Level6]

        @strawberry.type
        class Level4:
            id: int
            children: list[Level5]

        @strawberry.type
        class Level3:
            id: int
            children: list[Level4]

        @strawberry.type
        class Level2:
            id: int
            children: list[Level3]

        @strawberry.type
        class Level1:
            id: int
            children: list[Level2]

        @strawberry.type
        class Query:
            @strawberry.field
            def root(self) -> Level1:
                return Level1(id=1, children=[])

        def run():
            return strawberry.Schema(query=Query)

        benchmark(run)

    def test_resolve_10_levels_deep(self, benchmark: BenchmarkFixture):
        """Benchmark resolving a query 10 levels deep with branching factor 2."""

        @strawberry.type
        class DeepLeaf:
            id: int
            name: str

        @strawberry.type
        class Deep9:
            id: int

            @strawberry.field
            def children(self) -> list[DeepLeaf]:
                return [DeepLeaf(id=i, name=f"leaf_{i}") for i in range(2)]

        @strawberry.type
        class Deep8:
            id: int

            @strawberry.field
            def children(self) -> list[Deep9]:
                return [Deep9(id=i) for i in range(2)]

        @strawberry.type
        class Deep7:
            id: int

            @strawberry.field
            def children(self) -> list[Deep8]:
                return [Deep8(id=i) for i in range(2)]

        @strawberry.type
        class Deep6:
            id: int

            @strawberry.field
            def children(self) -> list[Deep7]:
                return [Deep7(id=i) for i in range(2)]

        @strawberry.type
        class Deep5:
            id: int

            @strawberry.field
            def children(self) -> list[Deep6]:
                return [Deep6(id=i) for i in range(2)]

        @strawberry.type
        class Deep4:
            id: int

            @strawberry.field
            def children(self) -> list[Deep5]:
                return [Deep5(id=i) for i in range(2)]

        @strawberry.type
        class Deep3:
            id: int

            @strawberry.field
            def children(self) -> list[Deep4]:
                return [Deep4(id=i) for i in range(2)]

        @strawberry.type
        class Deep2:
            id: int

            @strawberry.field
            def children(self) -> list[Deep3]:
                return [Deep3(id=i) for i in range(2)]

        @strawberry.type
        class Deep1:
            id: int

            @strawberry.field
            def children(self) -> list[Deep2]:
                return [Deep2(id=i) for i in range(2)]

        @strawberry.type
        class DeepRoot:
            @strawberry.field
            def root(self) -> Deep1:
                return Deep1(id=1)

        schema = strawberry.Schema(query=DeepRoot)

        query = """
            query {
                root {
                    id
                    children {
                        id
                        children {
                            id
                            children {
                                id
                                children {
                                    id
                                    children {
                                        id
                                        children {
                                            id
                                            children {
                                                id
                                                children {
                                                    id
                                                    children {
                                                        id
                                                        name
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors


@pytest.mark.benchmark
class TestLargeResultSetBenchmarks:
    """Benchmarks for queries returning ~1000 objects."""

    def test_resolve_1000_simple_objects(self, benchmark: BenchmarkFixture):
        """Benchmark resolving a query returning 1000 simple objects."""

        @strawberry.type
        class SimpleObject:
            id: int
            name: str
            value: float

        @strawberry.type
        class Query:
            @strawberry.field
            def items(self) -> list[SimpleObject]:
                return [
                    SimpleObject(id=i, name=f"item_{i}", value=float(i))
                    for i in range(1000)
                ]

        schema = strawberry.Schema(query=Query)
        query = "query { items { id name value } }"

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors

    def test_resolve_1000_objects_with_nested(self, benchmark: BenchmarkFixture):
        """Benchmark resolving 1000 objects each with a nested object."""

        @strawberry.type
        class NestedChild:
            id: int
            label: str

        @strawberry.type
        class ParentObject:
            id: int
            name: str

            @strawberry.field
            def child(self) -> NestedChild:
                return NestedChild(id=self.id, label=f"child_{self.id}")

        @strawberry.type
        class Query:
            @strawberry.field
            def items(self) -> list[ParentObject]:
                return [ParentObject(id=i, name=f"parent_{i}") for i in range(1000)]

        schema = strawberry.Schema(query=Query)
        query = "query { items { id name child { id label } } }"

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors

    def test_resolve_1000_objects_10_fields_each(self, benchmark: BenchmarkFixture):
        """Benchmark resolving 1000 objects with 10 fields each."""

        @strawberry.type
        class TenFieldObject:
            id: int
            field_1: str = "v1"
            field_2: str = "v2"
            field_3: str = "v3"
            field_4: str = "v4"
            field_5: str = "v5"
            field_6: int = 6
            field_7: int = 7
            field_8: float = 8.0
            field_9: float = 9.0

        @strawberry.type
        class Query:
            @strawberry.field
            def items(self) -> list[TenFieldObject]:
                return [TenFieldObject(id=i) for i in range(1000)]

        schema = strawberry.Schema(query=Query)
        query = """
            query {
                items {
                    id field_1 field_2 field_3 field_4 field_5
                    field_6 field_7 field_8 field_9
                }
            }
        """

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors

    def test_resolve_1000_objects_with_list_field(self, benchmark: BenchmarkFixture):
        """Benchmark resolving 1000 objects each with a list of 5 children."""

        @strawberry.type
        class ListChild:
            id: int
            name: str

        @strawberry.type
        class ListParent:
            id: int

            @strawberry.field
            def children(self) -> list[ListChild]:
                return [ListChild(id=j, name=f"child_{j}") for j in range(5)]

        @strawberry.type
        class Query:
            @strawberry.field
            def items(self) -> list[ListParent]:
                return [ListParent(id=i) for i in range(1000)]

        schema = strawberry.Schema(query=Query)
        query = "query { items { id children { id name } } }"

        def run():
            return asyncio.run(schema.execute(query))

        result = benchmark(run)
        assert not result.errors


@pytest.mark.benchmark
class TestObjectInstantiationBenchmarks:
    """Benchmarks for instantiating Strawberry type instances."""

    def test_instantiate_1000_simple_types(self, benchmark: BenchmarkFixture):
        """Benchmark instantiating 1000 simple Strawberry types."""

        @strawberry.type
        class SimpleType:
            id: int
            name: str
            value: float
            active: bool

        def run():
            return [
                SimpleType(id=i, name=f"name_{i}", value=float(i), active=i % 2 == 0)
                for i in range(1000)
            ]

        benchmark(run)

    def test_instantiate_1000_types_with_defaults(self, benchmark: BenchmarkFixture):
        """Benchmark instantiating 1000 types with default values."""

        @strawberry.type
        class TypeWithDefaults:
            id: int
            name: str = "default_name"
            value: float = 0.0
            active: bool = True
            tags: list[str] = strawberry.field(default_factory=list)

        def run():
            return [TypeWithDefaults(id=i) for i in range(1000)]

        benchmark(run)

    def test_instantiate_nested_1000_parents_5_children(self, benchmark: BenchmarkFixture):
        """Benchmark instantiating 1000 parents with 5 children each."""

        @strawberry.type
        class Child:
            id: int
            name: str

        @strawberry.type
        class Parent:
            id: int
            children: list[Child]

        def run():
            return [
                Parent(
                    id=i,
                    children=[Child(id=j, name=f"child_{j}") for j in range(5)]
                )
                for i in range(1000)
            ]

        benchmark(run)


@pytest.mark.benchmark
class TestFieldAccessBenchmarks:
    """Benchmarks for accessing StrawberryField attributes."""

    def test_iterate_1000_fields(self, benchmark: BenchmarkFixture):
        """Benchmark iterating over a type with many fields."""

        LargeType = create_type_with_n_fields("IterateLargeType", 100)

        def run():
            count = 0
            for _ in range(100):
                for field in dataclasses.fields(LargeType):
                    count += 1
            return count

        benchmark(run)

    def test_access_strawberry_definition_fields(self, benchmark: BenchmarkFixture):
        """Benchmark accessing fields via StrawberryObjectDefinition."""
        LargeType = create_type_with_n_fields("DefLargeType", 100)
        type_def: StrawberryObjectDefinition = LargeType.__strawberry_definition__

        def run():
            results = []
            for _ in range(100):
                for field in type_def.fields:
                    results.append((field.name, field.type, field.default))
            return results

        benchmark(run)


@strawberry.type
class BenchLeaf:
    id: int
    name: str


@strawberry.type
class BenchL9:
    id: int

    @strawberry.field
    def children(self) -> list[BenchLeaf]:
        return [BenchLeaf(id=i, name=f"leaf_{i}") for i in range(2)]


@strawberry.type
class BenchL8:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL9]:
        return [BenchL9(id=i) for i in range(2)]


@strawberry.type
class BenchL7:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL8]:
        return [BenchL8(id=i) for i in range(2)]


@strawberry.type
class BenchL6:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL7]:
        return [BenchL7(id=i) for i in range(2)]


@strawberry.type
class BenchL5:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL6]:
        return [BenchL6(id=i) for i in range(2)]


@strawberry.type
class BenchL4:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL5]:
        return [BenchL5(id=i) for i in range(2)]


@strawberry.type
class BenchL3:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL4]:
        return [BenchL4(id=i) for i in range(2)]


@strawberry.type
class BenchL2:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL3]:
        return [BenchL3(id=i) for i in range(2)]


@strawberry.type
class BenchL1:
    id: int

    @strawberry.field
    def children(self) -> list[BenchL2]:
        return [BenchL2(id=i) for i in range(2)]


@strawberry.type
class BenchDeepQuery:
    @strawberry.field
    def root(self) -> BenchL1:
        return BenchL1(id=1)


@strawberry.type
class BenchResultItem:
    id: int
    name: str
    value: float


@strawberry.type
class BenchResultQuery:
    @strawberry.field
    def items(self) -> list[BenchResultItem]:
        return [BenchResultItem(id=i, name=f"item_{i}", value=float(i)) for i in range(1000)]


@strawberry.type
class BenchInstType:
    id: int
    name: str
    value: float


@strawberry.interface
class BenchInterface:
    id: strawberry.ID


_manual_union_members: list = []
for _i in range(100):
    _cls = type(
        f"ManualUnionMember{_i}",
        (),
        {"__annotations__": {"id": int, "name": str}, "name": f"member_{_i}"}
    )
    _manual_union_members.append(strawberry.type(_cls))

ManualUnion = create_union_type("ManualUnion", _manual_union_members)


@strawberry.type
class BenchUnionQuery:
    @strawberry.field
    def search(self) -> list[ManualUnion]:
        return [_manual_union_members[i % 100](id=i) for i in range(1000)]


def run_manual_benchmarks():
    """Run benchmarks manually and print results for baseline recording."""
    print("=" * 80)
    print("DUCHESNE BASELINE BENCHMARKS - Pre-Migration Performance Metrics")
    print("=" * 80)
    print()

    results = []

    print("Running type creation benchmarks...")
    with TimingResult("Create 100 simple types (4 fields each)") as t:
        t.iterations = 100
        created_types = []
        for i in range(100):
            cls = type(
                f"ManualSimple{i}",
                (),
                {"__annotations__": {"id": int, "name": str, "value": float, "active": bool}}
            )
            created_types.append(strawberry.type(cls))
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    with TimingResult("Create 10 types with 100 fields each") as t:
        t.iterations = 10
        for i in range(10):
            create_type_with_n_fields(f"Manual100Fields{i}", 100)
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    with TimingResult("Create type with 1000 fields") as t:
        t.iterations = 1
        Type1000 = create_type_with_n_fields("Manual1000Fields", 1000)
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running schema building benchmarks...")

    impl_types = []
    with TimingResult("Create 100 interface implementations") as t:
        t.iterations = 100
        for i in range(100):
            cls = type(
                f"ManualImpl{i}",
                (BenchInterface,),
                {"__annotations__": {"id": strawberry.ID, "value": int}, "value": i}
            )
            impl_types.append(strawberry.type(cls))
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    @strawberry.type
    class ImplQuery:
        @strawberry.field
        def nodes(self) -> list[BenchInterface]:
            return []

    with TimingResult("Build schema with 100 interface implementations") as t:
        t.iterations = 1
        impl_schema = strawberry.Schema(query=ImplQuery, types=impl_types)
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running deep nesting benchmarks...")

    deep_schema = strawberry.Schema(query=BenchDeepQuery)
    deep_query = """
        query {
            root {
                id children {
                    id children {
                        id children {
                            id children {
                                id children {
                                    id children {
                                        id children {
                                            id children {
                                                id children {
                                                    id name
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    with TimingResult("Execute 10-level deep query (5 iterations)") as t:
        t.iterations = 5
        for _ in range(5):
            result = asyncio.run(deep_schema.execute(deep_query))
            assert not result.errors
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running large union benchmarks...")

    with TimingResult("Build schema with 100-member union") as t:
        t.iterations = 1
        union_schema = strawberry.Schema(query=BenchUnionQuery, types=_manual_union_members)
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    union_fragments = "\n".join(
        f"... on ManualUnionMember{i} {{ id name }}" for i in range(100)
    )
    union_query = f"""
        query {{
            search {{
                {union_fragments}
            }}
        }}
    """

    with TimingResult("Resolve 100-member union returning 1000 objects (5 iter)") as t:
        t.iterations = 5
        for _ in range(5):
            result = asyncio.run(union_schema.execute(union_query))
            assert not result.errors
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running large result set benchmarks...")

    result_schema = strawberry.Schema(query=BenchResultQuery)
    result_query = "query { items { id name value } }"

    with TimingResult("Execute query returning 1000 objects (5 iterations)") as t:
        t.iterations = 5
        for _ in range(5):
            result = asyncio.run(result_schema.execute(result_query))
            assert not result.errors
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running instantiation benchmarks...")

    with TimingResult("Instantiate 10000 type instances") as t:
        t.iterations = 10000
        instances = [BenchInstType(id=i, name=f"n{i}", value=float(i)) for i in range(10000)]
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print("Running field iteration benchmarks...")

    LargeFieldType = create_type_with_n_fields("ManualLargeFieldType", 100)

    with TimingResult("Iterate 100 fields x 1000 times (dataclasses.fields)") as t:
        t.iterations = 1000
        count = 0
        for _ in range(1000):
            for field in dataclasses.fields(LargeFieldType):
                count += 1
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    type_def: StrawberryObjectDefinition = LargeFieldType.__strawberry_definition__
    with TimingResult("Iterate 100 fields x 1000 times (strawberry definition)") as t:
        t.iterations = 1000
        count = 0
        for _ in range(1000):
            for field in type_def.fields:
                count += 1
    results.append((t.name, t.elapsed_ms, t.per_iteration_us))

    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Benchmark':<60} {'Total (ms)':>10} {'Per iter (us)':>14}")
    print("-" * 86)
    for name, total_ms, per_iter_us in results:
        print(f"{name:<60} {total_ms:>10.2f} {per_iter_us:>14.2f}")
    print()

    return results


if __name__ == "__main__":
    run_manual_benchmarks()
