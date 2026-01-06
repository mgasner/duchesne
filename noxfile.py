import itertools
from collections.abc import Callable
from typing import Any

import nox

nox.options.reuse_existing_virtualenvs = True
nox.options.error_on_external_run = True
nox.options.default_venv_backend = "uv"

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


def _install_gql_core(session: nox.Session, version: str) -> None:
    session.run("uv", "pip", "install", f"graphql-core=={version}", external=True)


gql_core_parametrize = nox.parametrize(
    "gql_core",
    GQL_CORE_VERSIONS,
)


def with_gql_core_parametrize(name: str, params: list[str]) -> Callable[[Any], Any]:
    # github cache doesn't support comma in the name, this is a workaround.
    arg_names = f"{name}, gql_core"
    combinations = list(itertools.product(params, GQL_CORE_VERSIONS))
    ids = [f"{name}-{comb[0]}__graphql-core-{comb[1]}" for comb in combinations]
    return lambda fn: nox.parametrize(arg_names, combinations, ids=ids)(fn)


@nox.session(python=PYTHON_VERSIONS, name="Tests", tags=["tests"])
@gql_core_parametrize
def tests(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)
    _install_gql_core(session, gql_core)
    markers = (
        ["-m", f"not {integration}", f"--ignore=tests/{integration}"]
        for integration in INTEGRATIONS
    )
    markers = [item for sublist in markers for item in sublist]

    session.run(
        "uv", "run", "--no-sync",
        "pytest",
        *COMMON_PYTEST_OPTIONS,
        *markers,
        external=True,
    )


@nox.session(python=["3.12"], name="Django tests", tags=["tests"])
@with_gql_core_parametrize("django", ["5.1.3", "5.0.9", "4.2.0"])
def tests_django(session: nox.Session, django: str, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)
    _install_gql_core(session, gql_core)
    session.run("uv", "pip", "install", f"django~={django}", external=True)
    session.run("uv", "pip", "install", "pytest-django", external=True)

    session.run("uv", "run", "--no-sync", "pytest", *COMMON_PYTEST_OPTIONS, "-m", "django", external=True)


@nox.session(python=["3.11"], name="Starlette tests", tags=["tests"])
@gql_core_parametrize
def tests_starlette(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run("uv", "pip", "install", "starlette", external=True)
    _install_gql_core(session, gql_core)
    session.run("uv", "run", "--no-sync", "pytest", *COMMON_PYTEST_OPTIONS, "-m", "asgi", external=True)


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

    session.run("uv", "pip", "install", integration, external=True)
    _install_gql_core(session, gql_core)
    if integration == "aiohttp":
        session.run("uv", "pip", "install", "pytest-aiohttp", external=True)
    elif integration == "channels":
        session.run("uv", "pip", "install", "pytest-django", external=True)
        session.run("uv", "pip", "install", "daphne", external=True)

    session.run("uv", "run", "--no-sync", "pytest", *COMMON_PYTEST_OPTIONS, "-m", integration, external=True)


@nox.session(
    python=["3.10", "3.11", "3.12", "3.13"],
    name="Pydantic V1 tests",
    tags=["tests", "pydantic"],
)
@gql_core_parametrize
def test_pydantic(session: nox.Session, gql_core: str) -> None:
    session.run_always("uv", "sync", "--group", "dev", external=True)

    session.run("uv", "pip", "install", "pydantic~=1.10", external=True)
    _install_gql_core(session, gql_core)
    session.run(
        "uv", "run", "--no-sync",
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

    session.run("uv", "pip", "install", "pydantic>=2.2", external=True)
    _install_gql_core(session, gql_core)
    session.run(
        "uv", "run", "--no-sync",
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

    session.run("uv", "pip", "install", "pyright", external=True)
    session.run("uv", "pip", "install", "pydantic", external=True)
    session.run("uv", "pip", "install", "mypy", external=True)
    session.run("uv", "pip", "install", "ty", external=True)

    session.run(
        "uv", "run", "--no-sync",
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

    session.run("uv", "pip", "install", "uvicorn", external=True)
    session.run("uv", "pip", "install", "starlette", external=True)

    session.run(
        "uv", "run", "--no-sync",
        "pytest",
        "--cov=.",
        "--cov-append",
        "--cov-report=xml",
        "tests/cli",
        "-vv",
        external=True,
    )
