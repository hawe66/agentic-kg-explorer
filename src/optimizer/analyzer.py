"""Failure Analyzer for detecting recurring failure patterns."""

import json
from collections import defaultdict
from datetime import datetime
from typing import Optional

from config.settings import get_settings
from src.agents.providers.router import get_provider
from src.graph.client import Neo4jClient

from .models import FailurePattern


class FailureAnalyzer:
    """Detect recurring failure patterns from evaluations."""

    def __init__(
        self,
        threshold: float = 0.6,
        min_samples: int = 5,
    ):
        """Initialize analyzer.

        Args:
            threshold: Score below this is considered a failure.
            min_samples: Minimum failures to create a pattern.
        """
        self.threshold = threshold
        self.min_samples = min_samples
        self._pattern_counter = 0

    def _get_client(self) -> Neo4jClient:
        """Get Neo4j client."""
        settings = get_settings()
        client = Neo4jClient(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        client.connect()
        return client

    def analyze(self, agent_name: str = None) -> list[FailurePattern]:
        """Query evaluations, cluster failures, generate patterns.

        Args:
            agent_name: Optional filter by agent. If None, analyze all.

        Returns:
            List of detected FailurePatterns.
        """
        # 1. Query low-scoring evaluations
        low_scores = self._query_low_scores(agent_name)

        if not low_scores:
            print("[FailureAnalyzer] No low-scoring evaluations found")
            return []

        # 2. Group by (agent_name, criterion_id)
        grouped = self._group_failures(low_scores)

        # 3. Generate patterns for groups with enough samples
        patterns = []
        for key, failures in grouped.items():
            if len(failures) >= self.min_samples:
                pattern = self._create_pattern(key, failures)
                if pattern:
                    patterns.append(pattern)

        # 4. Save patterns to Neo4j
        for pattern in patterns:
            self._save_pattern(pattern)

        return patterns

    def _query_low_scores(self, agent_name: str = None) -> list[dict]:
        """Query evaluations with low scores from Neo4j."""
        client = self._get_client()
        try:
            # Build query
            if agent_name:
                query = """
                    MATCH (e:Evaluation)
                    WHERE e.agent_name = $agent_name
                      AND e.composite_score < $threshold
                    RETURN e.id AS eval_id,
                           e.agent_name AS agent_name,
                           e.query AS query,
                           e.response AS response,
                           e.scores AS scores,
                           e.composite_score AS composite_score
                    ORDER BY e.created_at DESC
                    LIMIT 100
                """
                params = {"agent_name": agent_name, "threshold": self.threshold}
            else:
                query = """
                    MATCH (e:Evaluation)
                    WHERE e.composite_score < $threshold
                    RETURN e.id AS eval_id,
                           e.agent_name AS agent_name,
                           e.query AS query,
                           e.response AS response,
                           e.scores AS scores,
                           e.composite_score AS composite_score
                    ORDER BY e.created_at DESC
                    LIMIT 100
                """
                params = {"threshold": self.threshold}

            result = client.run_cypher(query, params)
            return [dict(row) for row in result]
        finally:
            client.close()

    def _group_failures(self, evaluations: list[dict]) -> dict[str, list[dict]]:
        """Group evaluations by agent and low-scoring criterion."""
        grouped = defaultdict(list)

        for eval_data in evaluations:
            agent = eval_data["agent_name"]
            scores_str = eval_data.get("scores", "{}")

            # Parse scores JSON
            try:
                scores = json.loads(scores_str) if isinstance(scores_str, str) else scores_str
            except json.JSONDecodeError:
                scores = {}

            # Find low-scoring criteria
            for criterion_id, score in (scores or {}).items():
                if score < self.threshold:
                    key = f"{agent}:{criterion_id}"
                    grouped[key].append({
                        "eval_id": eval_data["eval_id"],
                        "query": eval_data["query"],
                        "response": eval_data["response"],
                        "score": score,
                        "criterion_id": criterion_id,
                    })

        return grouped

    def _create_pattern(self, key: str, failures: list[dict]) -> Optional[FailurePattern]:
        """Create a FailurePattern from grouped failures."""
        parts = key.split(":", 1)
        if len(parts) != 2:
            return None

        agent_name, criterion_id = parts

        # Calculate statistics
        scores = [f["score"] for f in failures]
        avg_score = sum(scores) / len(scores)

        # Get sample queries and responses
        sample_queries = [f["query"] for f in failures[:5]]
        sample_responses = [f["response"][:200] for f in failures[:5] if f.get("response")]

        # Determine pattern type from criterion
        pattern_type = self._infer_pattern_type(criterion_id)

        # Generate description
        description = f"{agent_name} consistently scores low on {criterion_id} (avg: {avg_score:.2f})"

        # Generate hypotheses using LLM
        hypotheses = self._generate_hypotheses(
            agent_name, criterion_id, sample_queries, sample_responses, avg_score
        )

        # Generate pattern ID
        self._pattern_counter += 1
        date_str = datetime.now().strftime("%Y-%m")
        pattern_id = f"fp:{agent_name}:{criterion_id.split(':')[-1]}:{date_str}"

        return FailurePattern(
            id=pattern_id,
            agent_name=agent_name,
            criterion_id=criterion_id,
            pattern_type=pattern_type,
            description=description,
            frequency=len(failures),
            avg_score=avg_score,
            sample_queries=sample_queries,
            sample_responses=sample_responses,
            root_cause_hypotheses=hypotheses,
            suggested_fixes=[],
            status="detected",
        )

    def _infer_pattern_type(self, criterion_id: str) -> str:
        """Infer pattern type from criterion ID."""
        criterion = criterion_id.lower()

        if any(x in criterion for x in ["source", "citation", "grounding", "accuracy"]):
            return "output_quality"
        elif any(x in criterion for x in ["reasoning", "steps", "completeness"]):
            return "reasoning"
        elif any(x in criterion for x in ["retrieval", "query", "result", "template"]):
            return "retrieval"
        elif any(x in criterion for x in ["intent", "entity", "scope"]):
            return "classification"

        return "output_quality"

    def _generate_hypotheses(
        self,
        agent_name: str,
        criterion_id: str,
        sample_queries: list[str],
        sample_responses: list[str],
        avg_score: float,
    ) -> list[str]:
        """Use LLM to generate root cause hypotheses."""
        provider = get_provider()
        if provider is None:
            return self._fallback_hypotheses(criterion_id)

        # Format samples
        samples_text = ""
        for i, (q, r) in enumerate(zip(sample_queries, sample_responses or [""] * len(sample_queries))):
            samples_text += f"\nQuery {i+1}: {q}\n"
            if r:
                samples_text += f"Response excerpt: {r[:150]}...\n"

        prompt = f"""The {agent_name} agent consistently scores low on the "{criterion_id}" criterion.
Average score: {avg_score:.2f} (threshold: {self.threshold})

Sample failing cases:
{samples_text}

Generate 2-3 hypotheses for why the {agent_name} prompt might be causing this issue.
Focus on prompt-level issues that could be fixed by modifying the prompt text.

Output as a JSON list of strings:
["hypothesis 1", "hypothesis 2", "hypothesis 3"]

Only output the JSON, no other text."""

        try:
            response = provider.generate(prompt, max_tokens=300)

            # Parse JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                hypotheses = json.loads(json_match.group())
                return hypotheses[:3]
        except Exception as e:
            print(f"[FailureAnalyzer] Hypothesis generation failed: {e}")

        return self._fallback_hypotheses(criterion_id)

    def _fallback_hypotheses(self, criterion_id: str) -> list[str]:
        """Generate fallback hypotheses without LLM."""
        criterion = criterion_id.split(":")[-1].lower()

        fallbacks = {
            "source-citation": [
                "Prompt may not explicitly instruct to cite KG sources",
                "Source formatting instructions may be unclear",
            ],
            "answer-relevance": [
                "Prompt may lack clear instruction to directly answer the question",
                "Context formatting may be confusing the model",
            ],
            "reasoning-steps": [
                "Prompt may not require explicit reasoning steps",
                "Chain-of-thought instruction may be missing",
            ],
            "completeness": [
                "Prompt may not emphasize including all relevant information",
                "Instructions for handling multiple results may be unclear",
            ],
            "factual-accuracy": [
                "Prompt may allow too much creative interpretation",
                "Grounding instructions may be insufficiently strong",
            ],
            "intent-accuracy": [
                "Intent categories may not be clearly described",
                "Examples for each intent type may be insufficient",
            ],
            "entity-extraction": [
                "Entity extraction instructions may be too vague",
                "Entity format examples may be missing",
            ],
            "template-selection": [
                "Template selection criteria may be unclear",
                "Intent-to-template mapping may need more examples",
            ],
        }

        return fallbacks.get(criterion, [
            "Prompt instructions may be unclear or ambiguous",
            "Examples in the prompt may be insufficient",
        ])

    def _save_pattern(self, pattern: FailurePattern) -> bool:
        """Save FailurePattern to Neo4j."""
        client = self._get_client()
        try:
            client.run_cypher("""
                MERGE (fp:FailurePattern {id: $id})
                SET fp.agent_name = $agent_name,
                    fp.criterion_id = $criterion_id,
                    fp.pattern_type = $pattern_type,
                    fp.description = $description,
                    fp.frequency = $frequency,
                    fp.avg_score = $avg_score,
                    fp.sample_queries = $sample_queries,
                    fp.root_cause_hypotheses = $hypotheses,
                    fp.status = $status,
                    fp.created_at = datetime()
            """, {
                "id": pattern.id,
                "agent_name": pattern.agent_name,
                "criterion_id": pattern.criterion_id,
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "frequency": pattern.frequency,
                "avg_score": pattern.avg_score,
                "sample_queries": pattern.sample_queries,
                "hypotheses": pattern.root_cause_hypotheses,
                "status": pattern.status,
            })
            return True
        except Exception as e:
            print(f"[FailureAnalyzer] Failed to save pattern: {e}")
            return False
        finally:
            client.close()

    def get_patterns(
        self,
        status: str = None,
        agent_name: str = None,
    ) -> list[FailurePattern]:
        """Get existing failure patterns from Neo4j.

        Args:
            status: Filter by status (detected, reviewing, addressing, resolved).
            agent_name: Filter by agent.

        Returns:
            List of FailurePatterns.
        """
        client = self._get_client()
        try:
            where_clauses = []
            params = {}

            if status:
                where_clauses.append("fp.status = $status")
                params["status"] = status

            if agent_name:
                where_clauses.append("fp.agent_name = $agent_name")
                params["agent_name"] = agent_name

            where_str = ""
            if where_clauses:
                where_str = "WHERE " + " AND ".join(where_clauses)

            query = f"""
                MATCH (fp:FailurePattern)
                {where_str}
                RETURN fp
                ORDER BY fp.created_at DESC
            """

            result = client.run_cypher(query, params)
            patterns = []

            for row in result:
                fp = row["fp"]
                patterns.append(FailurePattern(
                    id=fp["id"],
                    agent_name=fp["agent_name"],
                    criterion_id=fp["criterion_id"],
                    pattern_type=fp.get("pattern_type", ""),
                    description=fp.get("description", ""),
                    frequency=fp.get("frequency", 0),
                    avg_score=fp.get("avg_score", 0.0),
                    sample_queries=fp.get("sample_queries", []),
                    root_cause_hypotheses=fp.get("root_cause_hypotheses", []),
                    status=fp.get("status", "detected"),
                ))

            return patterns
        finally:
            client.close()

    def update_pattern_status(self, pattern_id: str, status: str) -> bool:
        """Update pattern status."""
        client = self._get_client()
        try:
            client.run_cypher("""
                MATCH (fp:FailurePattern {id: $id})
                SET fp.status = $status
            """, {"id": pattern_id, "status": status})
            return True
        except Exception as e:
            print(f"[FailureAnalyzer] Failed to update status: {e}")
            return False
        finally:
            client.close()


# Singleton instance
_analyzer: Optional[FailureAnalyzer] = None


def get_analyzer() -> FailureAnalyzer:
    """Get or create singleton FailureAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FailureAnalyzer()
    return _analyzer
