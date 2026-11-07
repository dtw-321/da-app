"""
Eksekusi Python Script node dengan mitigasi berlapis.

PERINGATAN: ini BUKAN sandbox sejati. CPython tidak dapat diamankan sepenuhnya
dari dalam proses yang sama. Untuk produksi multi-user, jalankan node ini di
worker terisolasi (container/NSJail/subprocess terbatas) atau set
ALLOW_PYTHON_SCRIPT=false.
"""
import ast
from typing import Any, Dict, List

import pandas as pd


class SandboxError(Exception):
    """Script ditolak atau gagal dieksekusi."""


ALLOWED_MODULES = {
    "math", "statistics", "datetime", "json", "re", "itertools",
    "functools", "collections", "decimal", "numpy", "pandas",
}
BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "input", "globals", "locals", "vars",
    "dir", "getattr", "setattr", "delattr", "exit", "quit", "help",
    "breakpoint", "memoryview", "__import__",
}


def _guard_import(name: str, *_args: Any, **_kwargs: Any) -> Any:
    root = (name or "").split(".")[0]
    if root not in ALLOWED_MODULES:
        raise SandboxError("Import modul '{}' tidak diizinkan.".format(root))
    import importlib
    return importlib.import_module(name)


SAFE_BUILTINS: Dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "divmod": divmod, "enumerate": enumerate, "filter": filter, "float": float,
    "int": int, "isinstance": isinstance, "len": len, "list": list, "map": map,
    "max": max, "min": min, "print": print, "range": range, "round": round,
    "set": set, "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "zip": zip, "Exception": Exception, "ValueError": ValueError,
    "TypeError": TypeError, "KeyError": KeyError, "__import__": _guard_import,
}


def validate_script(source: str) -> None:
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise SandboxError("Syntax error pada baris {}: {}".format(exc.lineno, exc.msg))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_MODULES:
                    raise SandboxError("Import '{}' dilarang.".format(alias.name))
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_MODULES:
                raise SandboxError("Import dari '{}' dilarang.".format(node.module))
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise SandboxError("Akses atribut privat '{}' dilarang.".format(node.attr))
        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_NAMES or node.id.startswith("__"):
                raise SandboxError("Penggunaan '{}' dilarang.".format(node.id))


def run_script(source: str, inputs: List[pd.DataFrame]) -> pd.DataFrame:
    validate_script(source)
    # Satu namespace agar comprehension/lambda melihat variabel script.
    scope: Dict[str, Any] = {
        "__builtins__": SAFE_BUILTINS,
        "__name__": "dtanalitycs_sandbox",
        "inputs": [df.copy() for df in inputs],
        "pd": pd,
    }
    try:
        import numpy as np
        scope["np"] = np
    except ImportError:
        pass

    try:
        exec(compile(source, "<dtanalitycs_script>", "exec"), scope)  # noqa: S102
    except SandboxError:
        raise
    except Exception as exc:
        raise SandboxError("{}: {}".format(type(exc).__name__, exc))

    result = scope.get("df")
    if result is None:
        raise SandboxError("Script harus mendefinisikan variabel output 'df'.")
    if not isinstance(result, pd.DataFrame):
        raise SandboxError("Variabel 'df' harus bertipe pandas.DataFrame.")
    return result
