"""No model tools: execute pure-function candidates in a bounded restricted language.

This is a deliberately small Python subset, not a general hostile-code sandbox.
No imports, attribute traversal, reflection, file APIs or external objects enter it.
"""

import ast
import builtins
import copy
import json
import resource
import sys
from typing import Any

BUILTINS = (
    "len",
    "range",
    "enumerate",
    "zip",
    "sorted",
    "list",
    "tuple",
    "str",
    "int",
    "float",
    "bool",
    "abs",
    "min",
    "max",
    "sum",
    "round",
    "ValueError",
)
NODES = (
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.Expr,
    ast.If,
    ast.For,
    ast.While,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Raise,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Call,
    ast.keyword,
    ast.Attribute,
    ast.ListComp,
    ast.GeneratorExp,
    ast.comprehension,
    ast.Lambda,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Is,
    ast.IsNot,
)


def validate(code: str) -> ast.Module:
    tree = ast.parse(code)
    if any(not isinstance(node, ast.FunctionDef) for node in tree.body):
        raise ValueError("Only function definitions permitted at module scope")
    function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    for node in ast.walk(tree):
        if not isinstance(node, NODES):
            raise ValueError(f"Unsupported syntax: {type(node).__name__}")
        if isinstance(node, (ast.Name, ast.arg, ast.FunctionDef)):
            name = (
                node.id
                if isinstance(node, ast.Name)
                else node.arg
                if isinstance(node, ast.arg)
                else node.name
            )
            if "__" in name:
                raise ValueError("Dunder names forbidden")
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            raise ValueError("Decorators forbidden")
        if isinstance(node, ast.Attribute) and node.attr != "append":
            raise ValueError("Only list.append attribute permitted")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name)
            and node.func.id in {*BUILTINS, *function_names}
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
        ):
            raise ValueError("Call outside pure-function allowlist")
    return tree


def evaluate(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tree = validate(payload["code"])
    scope: dict[str, Any] = {"__builtins__": {name: getattr(builtins, name) for name in BUILTINS}}
    exec(compile(tree, "synthetic_solution.py", "exec"), scope)
    function = scope[payload["function"]]
    details = []
    for case in payload["cases"]:
        original = copy.deepcopy(case["input"])
        argument = copy.deepcopy(original)
        try:
            actual = function(argument)
            passed = "error" not in case and actual == case["expected"]
            if payload["function"] == "merge_intervals":
                passed = passed and argument == original
                if isinstance(actual, list):
                    passed = passed and actual is not argument
                    passed = passed and all(
                        item is not source for item in actual for source in argument
                    )
            details.append(
                {"case": case["name"], "passed": bool(passed), "actual": repr(actual)[:300]}
            )
        except Exception as exc:
            details.append(
                {
                    "case": case["name"],
                    "passed": type(exc).__name__ == case.get("error"),
                    "actual": type(exc).__name__,
                }
            )
    return details


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    # macOS rejects both AS and DATA limits here. CPU/wall limits and the AST
    # allowlist still apply; this is NOT a general hostile-code memory sandbox.
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    try:
        print(json.dumps({"details": evaluate(json.load(sys.stdin))}))
    except Exception as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {str(exc)[:300]}"}))
