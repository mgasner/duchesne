from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass

from .pyright import run_pyright
from .result import Result
from .ty import run_ty


@dataclass
class TypecheckResult:
    pyright: list[Result]
    ty: list[Result]


def typecheck(code: str, strict: bool = True) -> TypecheckResult:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        pyright_future = executor.submit(run_pyright, code, strict=strict)
        ty_future = executor.submit(run_ty, code, strict=strict)

        pyright_results = pyright_future.result()
        ty_results = ty_future.result()

    return TypecheckResult(pyright=pyright_results, ty=ty_results)
