"""Load and manage EvaluationCriteria from YAML config."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class EvaluationCriterion:
    """A single evaluation criterion."""

    id: str
    name: str
    principle_id: str
    agent_target: str
    description: str
    weight: float
    scoring_rubric: str
    version: str = "1.0.0"
    is_active: bool = True


@dataclass
class CriteriaSettings:
    """Global settings for evaluation."""

    min_composite_score: float = 0.6
    evaluation_sample_rate: float = 1.0
    max_response_length: int = 500
    feedback_enabled: bool = True


# Module-level cache
_criteria_cache: Optional[dict[str, list[EvaluationCriterion]]] = None
_settings_cache: Optional[CriteriaSettings] = None


def _get_config_path() -> Path:
    """Get path to evaluation_criteria.yaml."""
    return Path(__file__).resolve().parents[2] / "config" / "evaluation_criteria.yaml"


def load_criteria(force_reload: bool = False) -> dict[str, list[EvaluationCriterion]]:
    """Load all criteria from YAML, grouped by agent_target.

    Args:
        force_reload: If True, bypass cache and reload from file.

    Returns:
        Dict mapping agent_target to list of EvaluationCriterion.
    """
    global _criteria_cache

    if _criteria_cache is not None and not force_reload:
        return _criteria_cache

    config_path = _get_config_path()
    if not config_path.exists():
        print(f"[Critic] Warning: {config_path} not found, using empty criteria")
        _criteria_cache = {}
        return _criteria_cache

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    criteria_data = data.get("criteria", {})
    _criteria_cache = {}

    for agent_target, criteria_list in criteria_data.items():
        _criteria_cache[agent_target] = [
            EvaluationCriterion(
                id=c["id"],
                name=c["name"],
                principle_id=c["principle_id"],
                description=c["description"],
                weight=c["weight"],
                scoring_rubric=c.get("scoring_rubric", ""),
                agent_target=agent_target,
            )
            for c in criteria_list
        ]

    return _criteria_cache


def get_criteria_for_agent(agent_name: str) -> list[EvaluationCriterion]:
    """Get all active criteria for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., 'synthesizer', 'intent_classifier').

    Returns:
        List of EvaluationCriterion for this agent.
    """
    criteria = load_criteria()
    return [c for c in criteria.get(agent_name, []) if c.is_active]


def get_all_criteria() -> list[EvaluationCriterion]:
    """Get all criteria across all agents."""
    criteria = load_criteria()
    all_criteria = []
    for agent_criteria in criteria.values():
        all_criteria.extend(agent_criteria)
    return all_criteria


def get_settings(force_reload: bool = False) -> CriteriaSettings:
    """Load global evaluation settings from YAML.

    Args:
        force_reload: If True, bypass cache and reload from file.

    Returns:
        CriteriaSettings instance.
    """
    global _settings_cache

    if _settings_cache is not None and not force_reload:
        return _settings_cache

    config_path = _get_config_path()
    if not config_path.exists():
        _settings_cache = CriteriaSettings()
        return _settings_cache

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    settings_data = data.get("settings", {})
    _settings_cache = CriteriaSettings(
        min_composite_score=settings_data.get("min_composite_score", 0.6),
        evaluation_sample_rate=settings_data.get("evaluation_sample_rate", 1.0),
        max_response_length=settings_data.get("max_response_length", 500),
        feedback_enabled=settings_data.get("feedback_enabled", True),
    )

    return _settings_cache
