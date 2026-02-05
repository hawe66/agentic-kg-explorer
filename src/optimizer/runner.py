"""Test Runner for evaluating prompt variants."""

from pathlib import Path
from typing import Optional

import yaml

from src.agents.graph import run_agent
from src.critic.evaluator import get_evaluator

from .models import PromptVariant, TestQuery, TestResult


class TestRunner:
    """Run test queries and evaluate prompt variants."""

    def __init__(self, test_queries_path: Path = None):
        """Initialize runner.

        Args:
            test_queries_path: Path to test_queries.yaml.
        """
        self.test_queries_path = test_queries_path or (
            Path(__file__).parents[2] / "config" / "test_queries.yaml"
        )
        self.evaluator = get_evaluator()
        self._test_queries_cache: Optional[dict] = None

    def load_test_queries(self, agent_name: str = None) -> list[TestQuery]:
        """Load test queries from YAML config.

        Args:
            agent_name: Optional filter by agent.

        Returns:
            List of TestQuery objects.
        """
        if self._test_queries_cache is None:
            if self.test_queries_path.exists():
                with open(self.test_queries_path, "r", encoding="utf-8") as f:
                    self._test_queries_cache = yaml.safe_load(f) or {}
            else:
                self._test_queries_cache = {}

        queries = []

        if agent_name:
            agent_queries = self._test_queries_cache.get(agent_name, [])
            for q in agent_queries:
                queries.append(self._parse_test_query(q))
        else:
            for agent, agent_queries in self._test_queries_cache.items():
                for q in agent_queries:
                    queries.append(self._parse_test_query(q))

        return queries

    def _parse_test_query(self, data: dict) -> TestQuery:
        """Parse a test query from YAML data."""
        return TestQuery(
            query=data.get("query", ""),
            expected_intent=data.get("expected_intent"),
            expected_entities=data.get("expected_entities", []),
            expected_template=data.get("expected_template"),
            expected_retrieval=data.get("expected_retrieval"),
            min_confidence=data.get("min_confidence", 0.5),
            min_sources=data.get("min_sources", 0),
            min_results=data.get("min_results", 0),
            no_error=data.get("no_error", True),
        )

    def run_tests(
        self,
        agent_name: str,
        variants: list[PromptVariant],
        test_queries: list[TestQuery] = None,
    ) -> list[TestResult]:
        """Run tests for each variant, return ranked results.

        Args:
            agent_name: Agent being tested.
            variants: List of prompt variants to test.
            test_queries: Optional custom test queries.

        Returns:
            List of TestResult, sorted by performance_delta (best first).
        """
        if test_queries is None:
            test_queries = self.load_test_queries(agent_name)

        if not test_queries:
            print(f"[TestRunner] No test queries found for {agent_name}")
            return []

        results = []

        # Test baseline (current prompt) first
        print(f"[TestRunner] Testing baseline with {len(test_queries)} queries...")
        baseline_scores = self._run_test_suite(test_queries)

        # Test each variant
        for i, variant in enumerate(variants):
            print(f"[TestRunner] Testing variant {i+1}/{len(variants)}...")

            # TODO: Temporarily swap the prompt for testing
            # For now, we use the same pipeline and just evaluate differently
            # In a full implementation, we'd inject the variant prompt
            variant_scores = self._run_test_suite(test_queries, variant=variant)

            # Calculate performance delta
            delta = self._calculate_delta(baseline_scores, variant_scores)

            # Count passed/failed
            passed, failed = self._count_pass_fail(variant_scores, test_queries)

            result = TestResult(
                variant=variant,
                scores=variant_scores["avg_scores"],
                baseline_scores=baseline_scores["avg_scores"],
                per_query_scores=variant_scores["per_query"],
                performance_delta=delta,
                test_queries_count=len(test_queries),
                passed_count=passed,
                failed_count=failed,
            )
            results.append(result)

        # Sort by performance delta (best first)
        results.sort(key=lambda r: r.performance_delta, reverse=True)
        return results

    def _run_test_suite(
        self,
        test_queries: list[TestQuery],
        variant: PromptVariant = None,
    ) -> dict:
        """Run all test queries and collect scores.

        Args:
            test_queries: Queries to run.
            variant: Optional variant to test (if None, uses current).

        Returns:
            Dict with avg_scores and per_query results.
        """
        per_query = []
        all_scores = {}

        for tq in test_queries:
            try:
                # Run the agent pipeline
                # NOTE: In full implementation, we'd inject variant.prompt_content
                result = run_agent(tq.query, evaluate=False)

                # Evaluate the result
                evaluations = self.evaluator.evaluate_pipeline(result)

                # Collect scores
                query_scores = {}
                for ev in evaluations:
                    for criterion_id, score in ev.scores.items():
                        if criterion_id not in all_scores:
                            all_scores[criterion_id] = []
                        all_scores[criterion_id].append(score)
                        query_scores[criterion_id] = score

                # Check assertions
                assertions_passed = self._check_assertions(tq, result)

                per_query.append({
                    "query": tq.query,
                    "scores": query_scores,
                    "composite_score": evaluations[0].composite_score if evaluations else 0,
                    "assertions_passed": assertions_passed,
                    "intent": result.get("intent"),
                    "entities": result.get("entities"),
                    "confidence": result.get("confidence"),
                })

            except Exception as e:
                print(f"[TestRunner] Query failed: {tq.query[:50]}... - {e}")
                per_query.append({
                    "query": tq.query,
                    "scores": {},
                    "composite_score": 0,
                    "assertions_passed": False,
                    "error": str(e),
                })

        # Calculate averages
        avg_scores = {}
        for criterion_id, scores in all_scores.items():
            avg_scores[criterion_id] = sum(scores) / len(scores) if scores else 0

        return {
            "avg_scores": avg_scores,
            "per_query": per_query,
        }

    def _check_assertions(self, tq: TestQuery, result: dict) -> bool:
        """Check if result passes test query assertions."""
        # Check intent
        if tq.expected_intent:
            if result.get("intent") != tq.expected_intent:
                return False

        # Check entities
        if tq.expected_entities:
            extracted = result.get("entities") or []
            for expected in tq.expected_entities:
                if expected not in extracted:
                    return False

        # Check confidence
        confidence = result.get("confidence") or 0
        if confidence < tq.min_confidence:
            return False

        # Check sources
        sources = result.get("sources") or []
        if len(sources) < tq.min_sources:
            return False

        # Check results
        kg_results = result.get("kg_results") or []
        if len(kg_results) < tq.min_results:
            return False

        # Check error
        if tq.no_error and result.get("error"):
            return False

        return True

    def _calculate_delta(self, baseline: dict, variant: dict) -> float:
        """Calculate overall performance delta."""
        baseline_scores = baseline.get("avg_scores", {})
        variant_scores = variant.get("avg_scores", {})

        if not baseline_scores:
            return 0.0

        # Calculate average improvement across all criteria
        deltas = []
        for criterion_id, baseline_score in baseline_scores.items():
            variant_score = variant_scores.get(criterion_id, baseline_score)
            deltas.append(variant_score - baseline_score)

        return sum(deltas) / len(deltas) if deltas else 0.0

    def _count_pass_fail(
        self,
        scores: dict,
        test_queries: list[TestQuery],
    ) -> tuple[int, int]:
        """Count passed and failed tests."""
        passed = 0
        failed = 0

        for pq in scores.get("per_query", []):
            if pq.get("assertions_passed", False):
                passed += 1
            else:
                failed += 1

        return passed, failed

    def run_single_test(self, query: str) -> dict:
        """Run a single test query and return detailed results.

        Args:
            query: The query to test.

        Returns:
            Dict with result details.
        """
        try:
            result = run_agent(query, evaluate=True)
            evaluations = self.evaluator.evaluate_pipeline(result)

            return {
                "success": True,
                "query": query,
                "answer": result.get("answer"),
                "intent": result.get("intent"),
                "entities": result.get("entities"),
                "confidence": result.get("confidence"),
                "sources_count": len(result.get("sources") or []),
                "kg_results_count": len(result.get("kg_results") or []),
                "evaluations": [
                    {
                        "agent": ev.agent_name,
                        "composite_score": ev.composite_score,
                        "scores": ev.scores,
                    }
                    for ev in evaluations
                ],
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e),
            }
