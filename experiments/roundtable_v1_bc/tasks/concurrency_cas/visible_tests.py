"""Visible requirements; run with Python from this initial snapshot."""

import copy
import json
import math
from pathlib import Path

from solution import solve

for case in json.loads(Path(__file__).with_name("visible.json").read_text()):
    arg = copy.deepcopy(case["input"])
    try:
        actual = solve(arg)
    except ValueError:
        assert case.get("error") == "ValueError"
    else:
        assert "error" not in case
        expected = case["expected"]
        assert (
            math.isclose(actual, expected, rel_tol=1e-12, abs_tol=0)
            if type(expected) is float
            else actual == expected
        )
    if case["nonmutation"]:
        assert arg == case["input"]
print("VISIBLE_PASS")
