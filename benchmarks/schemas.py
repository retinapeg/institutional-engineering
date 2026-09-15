import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Task(Record):
    task_id: str
    domain: Literal["physics", "mathematics", "statistics", "software"]
    task: str
    ground_truth_or_acceptance: dict[str, JsonValue]
    matched_role: str
    mismatched_role: str
    verification_method: str
    difficulty_prior: Literal["medium", "high"]
    fixture: str | None = None


class Change(Record):
    path: Literal["solution.py"]
    content: str = Field(max_length=12000)


class BenchmarkResponse(Record):
    answer: dict[str, JsonValue]
    concise_method_summary: str = Field(max_length=1800)
    assumptions: list[str] = Field(max_length=6)
    confidence: float = Field(ge=0, le=1)
    proposed_verification: list[str] = Field(max_length=6)
    files: list[Change] = Field(default_factory=list, max_length=1)


class Cell(Record):
    task_id: str
    provider: Literal["claude", "codex"]
    model: Literal["sonnet", "gpt-5.6-terra", "gpt-5.6-sol"]
    condition: Literal["baseline", "matched", "mismatched"]
    repeat: Literal[1, 2]
    sweep: Literal["primary", "secondary"] = "primary"

    @property
    def key(self) -> str:
        value = [self.task_id, self.model, self.condition, self.repeat]
        return hashlib.sha256(json.dumps(value).encode()).hexdigest()[:24]


class Grade(Record):
    score: float = Field(ge=0, le=1)
    tests_passed: int
    tests_total: int
    details: list[dict[str, JsonValue]]


class Result(Record):
    key: str
    run_id: str
    task_id: str
    domain: str
    condition: str
    role: str
    provider: str
    model: str
    repeat: int
    sweep: str
    task_text: str
    difficulty_prior: str
    response: BenchmarkResponse | None = None
    response_text: str = ""
    schema_success: bool = False
    call_success: bool = False
    success: bool = False
    objective_score: float = 0
    tests_passed: int = 0
    tests_total: int = 0
    verification_details: list[dict[str, JsonValue]] = Field(default_factory=list)
    latency_seconds: float = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    reported_usage_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    relative_cost_class: str
    actual_marginal_cost: str = "UNKNOWN"
    error_category: str | None = None
    error: str | None = None
    started_at: float
    ended_at: float
    repairs: int = 0
    model_call_attempted: bool = True
