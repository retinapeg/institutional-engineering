from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpertReport(Record):
    key_observation: str
    proposed_approach: str
    important_assumptions: list[str]
    biggest_risk: str
    evidence: list[str]
    recommended_action: str
    confidence: float = Field(ge=0, le=1)


class Challenge(Record):
    major_flaw: str
    disagreement: str
    missing_fact: str


class Decision(Record):
    deliverable: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=8)
    agreed: list[str]
    disputed: list[str]
    unknown: list[str]
    decision: str
    build_plan: list[str] = Field(min_length=1, max_length=6)
    scoring_opportunities: list[str] = Field(default_factory=list)
    winning_demo_moment: str = ""


class FileChange(Record):
    path: str
    content: str  # No deletion operation in v1.


class BuildTask(Record):
    summary: str
    files: list[FileChange] = Field(max_length=20)
    run_command: str
    limitations: list[str]
    pitch_outline: list[str] = Field(default_factory=list)
    fallback: str = ""
    question: str = ""


class QAResult(Record):
    verdict: Literal["PASS", "FIX", "BLOCKED"]
    critical_findings: list[str]
    evidence: list[str]
    acceptance_met: bool
    limitations: list[str]
    regression_tests: list[FileChange] = Field(default_factory=list, max_length=4)


class RepairResult(BuildTask):
    resolved_findings: list[str]
