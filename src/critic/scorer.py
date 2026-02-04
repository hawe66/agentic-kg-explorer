"""Scoring logic for individual evaluation criteria."""

from typing import Optional

from src.agents.providers.router import get_provider

from .criteria import EvaluationCriterion


def score_criterion(
    criterion: EvaluationCriterion,
    query: str,
    response: str,
    context: Optional[dict] = None,
) -> float:
    """Score a response against a single criterion using LLM.

    Args:
        criterion: The evaluation criterion to score against.
        query: Original user query.
        response: Agent's response to evaluate.
        context: Optional context (kg_results, vector_results, etc.).

    Returns:
        Score from 0.0 to 1.0.
    """
    provider = get_provider()
    if provider is None:
        # Fallback to heuristic scoring if no LLM available
        return _heuristic_score(criterion, query, response, context)

    # Build scoring prompt
    prompt = _build_scoring_prompt(criterion, query, response, context)

    try:
        result = provider.generate(prompt, max_tokens=50)
        score = _parse_score(result)
        return score
    except Exception as e:
        print(f"[Scorer] LLM scoring failed for {criterion.id}: {e}")
        return _heuristic_score(criterion, query, response, context)


def _build_scoring_prompt(
    criterion: EvaluationCriterion,
    query: str,
    response: str,
    context: Optional[dict] = None,
) -> str:
    """Build the LLM prompt for scoring."""
    context_str = ""
    if context:
        kg_count = len(context.get("kg_results") or [])
        vector_count = len(context.get("vector_results") or [])
        sources = context.get("sources") or []
        context_str = f"""
Context:
- KG results retrieved: {kg_count}
- Vector results retrieved: {vector_count}
- Sources cited: {len(sources)}
"""

    return f"""You are evaluating an AI assistant's response quality.

Criterion: {criterion.name}
Description: {criterion.description}

Scoring Rubric:
{criterion.scoring_rubric}

User Query: {query}

Assistant Response: {response[:1000]}
{context_str}

Based on the rubric above, assign a score from 0.0 to 1.0.
Output ONLY the numeric score (e.g., "0.8"). No explanation needed.

Score:"""


def _parse_score(result: str) -> float:
    """Parse numeric score from LLM output."""
    result = result.strip()

    # Try to extract first number
    import re

    match = re.search(r"(\d+\.?\d*)", result)
    if match:
        score = float(match.group(1))
        # Normalize if > 1 (e.g., percentage)
        if score > 1.0:
            score = score / 100.0
        return max(0.0, min(1.0, score))

    # Default if parsing fails
    return 0.5


def _heuristic_score(
    criterion: EvaluationCriterion,
    query: str,
    response: str,
    context: Optional[dict] = None,
) -> float:
    """Fallback heuristic scoring when LLM is unavailable."""
    criterion_id = criterion.id
    response = response or ""  # Handle None response

    # Simple heuristics per criterion type
    if criterion_id == "ec:answer-relevance":
        # Check if response is non-empty and reasonable length
        if not response or len(response) < 20:
            return 0.2
        return 0.7

    elif criterion_id == "ec:source-citation":
        # Check for citation patterns
        sources = (context or {}).get("sources") or []
        if sources and len(sources) >= 2:
            return 0.9
        elif sources:
            return 0.6
        return 0.3

    elif criterion_id == "ec:factual-accuracy":
        # Can't verify without LLM, assume moderate
        kg_results = (context or {}).get("kg_results") or []
        if kg_results:
            return 0.7
        return 0.5

    elif criterion_id == "ec:reasoning-steps":
        # Check for reasoning indicators
        reasoning_keywords = ["because", "therefore", "since", "결과", "따라서", "때문"]
        if any(kw in response.lower() for kw in reasoning_keywords):
            return 0.7
        return 0.4

    elif criterion_id == "ec:completeness":
        # Check response length relative to context
        kg_count = len((context or {}).get("kg_results") or [])
        if kg_count > 0 and len(response) > 200:
            return 0.7
        return 0.5

    elif criterion_id == "ec:conciseness":
        # Penalize very long responses
        if len(response) > 2000:
            return 0.4
        elif len(response) > 1000:
            return 0.6
        return 0.8

    elif criterion_id == "ec:safety":
        # Assume safe unless obvious issues
        return 1.0

    elif criterion_id == "ec:intent-accuracy":
        # Can't verify intent accuracy without ground truth
        return 0.7

    elif criterion_id == "ec:entity-extraction":
        entities = (context or {}).get("entities") or []
        if entities and len(entities) >= 1:
            return 0.8
        return 0.4

    elif criterion_id == "ec:scope-detection":
        intent = (context or {}).get("intent", "")
        # Assume correct unless out_of_scope with results
        if intent == "out_of_scope":
            return 0.9
        return 0.7

    elif criterion_id == "ec:template-selection":
        strategy = (context or {}).get("search_strategy") or {}
        template = strategy.get("cypher_template")
        if template:
            return 0.8
        return 0.4

    elif criterion_id == "ec:retrieval-mode":
        strategy = (context or {}).get("search_strategy") or {}
        mode = strategy.get("retrieval_type")
        if mode:
            return 0.7
        return 0.5

    elif criterion_id == "ec:parameter-binding":
        strategy = (context or {}).get("search_strategy") or {}
        params = strategy.get("parameters") or {}
        if params:
            return 0.8
        return 0.5

    elif criterion_id == "ec:query-execution":
        error = (context or {}).get("error")
        if error:
            return 0.0
        kg_results = (context or {}).get("kg_results") or []
        if kg_results:
            return 1.0
        return 0.5

    elif criterion_id == "ec:result-relevance":
        kg_results = (context or {}).get("kg_results") or []
        if kg_results:
            return 0.7
        return 0.3

    # Default
    return 0.5


def calculate_composite_score(
    scores: dict[str, float],
    criteria: list[EvaluationCriterion],
) -> float:
    """Calculate weighted composite score.

    Args:
        scores: Dict mapping criterion_id to score.
        criteria: List of criteria with weights.

    Returns:
        Weighted average score from 0.0 to 1.0.
    """
    if not scores or not criteria:
        return 0.0

    total_weight = 0.0
    weighted_sum = 0.0

    for c in criteria:
        if c.id in scores:
            weighted_sum += scores[c.id] * c.weight
            total_weight += c.weight

    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight
