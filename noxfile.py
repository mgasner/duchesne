import itertools
from collections.abc import Callable
from typing import Any

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True

PYTHON_VERSIONS = ["3.14", "3.13", "3.12", "3.11", "3.10"]

GQL_CORE_VERSIONS = [
    "3.2.6",
    "3.3.0a9",
]

COMMON_PYTEST_OPTIONS = [
    "--cov=.",
    "--cov-append",
    "--cov-report=xml",
    "-n",
    "auto",
    "--showlocals",
    "-vv",
    "--ignore=tests/typecheckers",
    "--ignore=tests/cli",
    "--ignore=tests/benchmarks",
    "--ignore=tests/experimental/pydantic",
]

INTEGRATIONS = [
    "asgi",
    "aiohttp",
    "chalice",
    "channels",
    "django",
    "fastapi",
    "flask",
    "quart",
    "sanic",
    "litestar",
    "pydantic",
]


def _gql_core_with_arg(version: str) -> list[str]:
    return ["--with", f"graphql-core=={version}"]


gql_core_parametrize = nox.parametrize(
    "gql_core",
    GQL_CORE_VERSIONS,
)


def with_gql_core_parametrize(name: str, params: list[str]) -> Callable[[Any], Any]:
    arg_names = f"{name}, gql_core"
    combinations = list(itertools.product(params, GQL_CORE_VERSIONS))
    ids = [f"{name}-{comb[0]}__graphql-core-{comb[1]}" for comb in combinations]
    return lambda fn: nox.parametrize(arg_names, combinations, ids=ids)(fn)


@nox.session(python=PYTHON_VERSIONS, name="Tests", tags=["tests"])
@gql_core_parametrize
def tests(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)
    markers = (
        ["-m", f"not {integration}", f"--ignore=tests/{integration}"]
        for integration in INTEGRATIONS
    )
    markers = [item for sublist in markers for item in sublist]

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        "pytest",
        *COMMON_PYTEST_OPTIONS,
        *markers,
        external=True,
    )


@nox.session(python=["3.12"], name="Django tests", tags=["tests"])
@with_gql_core_parametrize("django", ["5.1.3", "5.0.9", "4.2.0"])
def tests_django(session: nox.Session, django: str, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        "--with", f"django~={django}",
        "--with", "pytest-django",
        "pytest", *COMMON_PYTEST_OPTIONS, "-m", "django",
        external=True,
    )


@nox.session(python=["3.11"], name="Starlette tests", tags=["tests"])
@gql_core_parametrize
def tests_starlette(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        "--with", "starlette",
        "pytest", *COMMON_PYTEST_OPTIONS, "-m", "asgi",
        external=True,
    )


@nox.session(python=["3.11"], name="Test integrations", tags=["tests"])
@with_gql_core_parametrize(
    "integration",
    [
        "aiohttp",
        "chalice",
        "channels",
        "fastapi",
        "flask",
        "quart",
        "sanic",
        "litestar",
    ],
)
def tests_integrations(session: nox.Session, integration: str, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    with_args = ["--with", integration]
    if integration == "aiohttp":
        with_args.extend(["--with", "pytest-aiohttp"])
    elif integration == "channels":
        with_args.extend(["--with", "pytest-django", "--with", "daphne"])

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        *with_args,
        "pytest", *COMMON_PYTEST_OPTIONS, "-m", integration,
        external=True,
    )


@nox.session(
    python=["3.10", "3.11", "3.12", "3.13"],
    name="Pydantic V1 tests",
    tags=["tests", "pydantic"],
)
@gql_core_parametrize
def test_pydantic(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        "--with", "pydantic~=1.10",
        "pytest",
        "--cov=.",
        "--cov-append",
        "--cov-report=xml",
        "-m",
        "pydantic",
        "--ignore=tests/cli",
        "--ignore=tests/benchmarks",
        external=True,
    )


@nox.session(python=PYTHON_VERSIONS, name="Pydantic tests", tags=["tests", "pydantic"])
@gql_core_parametrize
def test_pydantic_v2(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run(
        "uv", "run",
        *_gql_core_with_arg(gql_core),
        "--with", "pydantic>=2.2",
        "pytest",
        "--cov=.",
        "--cov-append",
        "--cov-report=xml",
        "-m",
        "pydantic",
        "--ignore=tests/cli",
        "--ignore=tests/benchmarks",
        external=True,
    )


@nox.session(python=PYTHON_VERSIONS, name="Type checkers tests", tags=["tests"])
def tests_typecheckers(session: nox.Session) -> None:
    session.run_always("uv", "sync", "--group", "dev", "--group", "integrations", external=True)

    session.run(
        "uv", "run",
        "--with", "pyright",
        "--with", "pydantic",
        "--with", "ty",
        "pytest",
        "--cov=.",
        "--cov-append",
        "--cov-report=xml",
        "tests/typecheckers",
        "-vv",
        external=True,
    )


@nox.session(python=PYTHON_VERSIONS, name="CLI tests", tags=["tests"])
def tests_cli(session: nox.Session) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run(
        "uv", "run",
        "--with", "uvicorn",
        "--with", "starlette",
        "pytest",
        "--cov=.",
        "--cov-append",
        "--cov-report=xml",
        "tests/cli",
        "-vv",
        external=True,
    )
