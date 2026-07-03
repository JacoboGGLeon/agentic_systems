"""Self-contained demo skill tools for ``load_skill(...)`` tests."""

from __future__ import annotations


def sumar(a: int, b: int) -> dict:
    return {"operation": "sumar", "result": a + b}


def restar(a: int, b: int) -> dict:
    return {"operation": "restar", "result": a - b}


def multiplicar(a: int, b: int) -> dict:
    return {"operation": "multiplicar", "result": a * b}


def dividir(a: int, b: int) -> dict:
    if b == 0:
        return {"operation": "dividir", "ok": False, "error": "division_by_zero"}
    result = a / b
    if float(result).is_integer():
        result = int(result)
    return {"operation": "dividir", "result": result}


def number_to_text(n: int) -> dict:
    mapping = {42: "cuarenta y dos"}
    return {"operation": "number_to_text", "number": n, "text": mapping.get(n, str(n))}


def read_md(path: str) -> dict:
    return {"operation": "read_md", "markdown": "leido", "path": path, "content": ""}


__all__ = ["sumar", "restar", "multiplicar", "dividir", "number_to_text", "read_md"]
