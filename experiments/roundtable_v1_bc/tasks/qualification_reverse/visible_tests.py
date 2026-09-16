"""Public deterministic operational scenario, never a benchmark candidate."""
import json
from pathlib import Path
from solution import solve
for case in json.loads(Path(__file__).with_name("visible.json").read_text()):
    actual=solve(case["input"])
    assert type(actual) is type(case["expected"]) and actual==case["expected"]
print("VISIBLE_PASS")
