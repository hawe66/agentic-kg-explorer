"""Data models for Prompt Optimizer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FailurePattern:
    """Represents a recurring failure pattern detected from evaluations."""

    id: str  # "fp:synthesizer:source-citation:2026-02"
    agent_name: str  # "synthesizer"
    criterion_id: str  # "ec:source-citation"
    pattern_type: str  # "output_quality" | "reasoning" | "retrieval" | "classification"
    description: str  # "Synthesizer consistently fails to cite KG sources"
    frequency: int  # Number of low-score evaluations
    avg_score: float  # Average score for this criterion
    sample_queries: list[str] = field(default_factory=list)  # Example queries
    sample_responses: list[str] = field(default_factory=list)  # Example responses
    root_cause_hypotheses: list[str] = field(default_factory=list)  # LLM-generated
    suggested_fixes: list[str] = field(default_factory=list)  # Potential changes
    status: str = "detected"  # "detected" | "reviewing" | "addressing" | "resolved"
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    @property
    def pattern_key(self) -> str:
        """Unique key for grouping: agent_name:criterion_id."""
        return f"{self.agent_name}:{self.criterion_id}"


@dataclass
class PromptVariant:
    """A generated prompt variant to address a failure pattern."""

    id: str  # "var:synthesizer:001"
    agent_name: str
    prompt_content: str  # Full new prompt text
    rationale: str  # Why this change helps
    addresses_hypotheses: list[int] = field(default_factory=list)  # Indices
    failure_pattern_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PromptVersion:
    """A versioned prompt stored in the registry."""

    id: str  # "pv:synthesizer@1.2.0"
    agent_name: str  # "synthesizer"
    version: str  # "1.2.0" (semver)
    prompt_content: str  # Full prompt text
    prompt_hash: str  # SHA256 of content
    prompt_path: str  # "config/prompts/synthesizer/v1.2.0.txt"
    is_active: bool = False  # Only one active per agent
    user_approved: bool = False  # Human approved
    parent_version: Optional[str] = None  # "pv:synthesizer@1.1.0"
    failure_pattern_id: Optional[str] = None  # Pattern this addresses
    performance_delta: float = 0.0  # Improvement from parent
    test_results: Optional[dict] = None  # Test run summary
    rationale: str = ""  # Why this change was made
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


@dataclass
class TestResult:
    """Result of testing a prompt variant."""

    variant: PromptVariant
    scores: dict[str, float]  # criterion_id -> avg score
    baseline_scores: dict[str, float]  # Current prompt scores
    per_query_scores: list[dict]  # Detailed per-query results
    performance_delta: float  # Overall improvement
    test_queries_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def pass_rate(self) -> float:
        """Percentage of tests passed."""
        if self.test_queries_count == 0:
            return 0.0
        return self.passed_count / self.test_queries_count


@dataclass
class TestQuery:
    """A test query for evaluating prompts."""

    query: str
    expected_intent: Optional[str] = None
    expected_entities: list[str] = field(default_factory=list)
    expected_template: Optional[str] = None
    expected_retrieval: Optional[str] = None
    min_confidence: float = 0.5
    min_sources: int = 0
    min_results: int = 0
    no_error: bool = True
