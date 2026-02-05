"""CriticEvaluator orchestrates evaluation of agent outputs."""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config.settings import get_settings as get_app_settings
from src.agents.providers.router import get_provider
from src.graph.client import Neo4jClient

from .criteria import (
    EvaluationCriterion,
    get_criteria_for_agent,
    get_settings as get_eval_settings,
)
from .scorer import calculate_composite_score, score_criterion


@dataclass
class Evaluation:
    """Result of evaluating an agent's output."""

    id: str
    agent_name: str
    query: str
    response: str
    scores: dict[str, float]
    composite_score: float
    feedback: str
    created_at: datetime = field(default_factory=datetime.now)
    conversation_id: Optional[str] = None


class CriticEvaluator:
    """Evaluates agent outputs against EvaluationCriteria."""

    def __init__(self):
        self._eval_counter = 0

    def evaluate(
        self,
        agent_name: str,
        query: str,
        response: str,
        context: Optional[dict] = None,
        conversation_id: Optional[str] = None,
    ) -> Optional[Evaluation]:
        """Score response against all criteria for this agent.

        Args:
            agent_name: Name of the agent being evaluated.
            query: Original user query.
            response: Agent's response to evaluate.
            context: Optional context dict with kg_results, vector_results, etc.
            conversation_id: Optional session/conversation ID.

        Returns:
            Evaluation object, or None if sampling excludes this evaluation.
        """
        settings = get_eval_settings()

        # Apply sampling rate
        if settings.evaluation_sample_rate < 1.0:
            if random.random() > settings.evaluation_sample_rate:
                return None

        # Get criteria for this agent
        criteria = get_criteria_for_agent(agent_name)
        if not criteria:
            print(f"[CriticEvaluator] No criteria found for agent: {agent_name}")
            return None

        # Score each criterion
        scores = {}
        for criterion in criteria:
            score = score_criterion(criterion, query, response, context)
            scores[criterion.id] = score

        # Calculate composite score
        composite = calculate_composite_score(scores, criteria)

        # Generate feedback if enabled
        feedback = ""
        if settings.feedback_enabled and composite < settings.min_composite_score:
            feedback = self._generate_feedback(criteria, scores, query, response)

        # Create evaluation
        self._eval_counter += 1
        eval_id = f"eval:{datetime.now().strftime('%Y%m%d')}-{self._eval_counter:04d}"

        # Truncate response for storage
        truncated_response = response[: settings.max_response_length]
        if len(response) > settings.max_response_length:
            truncated_response += "..."

        evaluation = Evaluation(
            id=eval_id,
            agent_name=agent_name,
            query=query,
            response=truncated_response,
            scores=scores,
            composite_score=composite,
            feedback=feedback,
            conversation_id=conversation_id,
        )

        return evaluation

    def evaluate_pipeline(
        self,
        state: dict,
        conversation_id: Optional[str] = None,
    ) -> list[Evaluation]:
        """Evaluate multiple agents from a pipeline state.

        Args:
            state: AgentState dict with results from all pipeline stages.
            conversation_id: Optional session ID.

        Returns:
            List of Evaluation objects for each evaluated agent.
        """
        evaluations = []
        query = state.get("user_query", "")

        # Evaluate synthesizer (main output)
        answer = state.get("answer") or ""
        if answer:
            eval_result = self.evaluate(
                agent_name="synthesizer",
                query=query,
                response=answer,
                context={
                    "kg_results": state.get("kg_results") or [],
                    "vector_results": state.get("vector_results") or [],
                    "sources": state.get("sources") or [],
                    "web_results": state.get("web_results") or [],
                    "intent": state.get("intent"),
                    "entities": state.get("entities") or [],
                },
                conversation_id=conversation_id,
            )
            if eval_result:
                evaluations.append(eval_result)

        # Evaluate intent classifier
        intent = state.get("intent")
        entities = state.get("entities") or []
        if intent:
            intent_response = f"Intent: {intent}, Entities: {entities}"
            eval_result = self.evaluate(
                agent_name="intent_classifier",
                query=query,
                response=intent_response,
                context={
                    "intent": intent,
                    "entities": entities,
                },
                conversation_id=conversation_id,
            )
            if eval_result:
                evaluations.append(eval_result)

        # Evaluate search planner
        strategy = state.get("search_strategy") or {}
        if strategy:
            planner_response = json.dumps(strategy, ensure_ascii=False, default=str)
            eval_result = self.evaluate(
                agent_name="search_planner",
                query=query,
                response=planner_response,
                context={
                    "search_strategy": strategy,
                    "intent": intent,
                    "entities": entities,
                },
                conversation_id=conversation_id,
            )
            if eval_result:
                evaluations.append(eval_result)

        # Evaluate graph retriever
        kg_results = state.get("kg_results") or []
        cypher_executed = state.get("cypher_executed") or []
        error = state.get("error")
        retriever_response = f"Results: {len(kg_results)}, Queries: {len(cypher_executed)}"
        if error:
            retriever_response += f", Error: {error}"

        eval_result = self.evaluate(
            agent_name="graph_retriever",
            query=query,
            response=retriever_response,
            context={
                "kg_results": kg_results,
                "cypher_executed": cypher_executed,
                "error": error,
                "search_strategy": strategy,
            },
            conversation_id=conversation_id,
        )
        if eval_result:
            evaluations.append(eval_result)

        return evaluations

    def _generate_feedback(
        self,
        criteria: list[EvaluationCriterion],
        scores: dict[str, float],
        query: str,
        response: str,
    ) -> str:
        """Generate improvement feedback for low-scoring responses."""
        provider = get_provider()
        if provider is None:
            return self._heuristic_feedback(criteria, scores)

        # Find lowest scoring criteria
        low_scores = [
            (c, scores.get(c.id, 0))
            for c in criteria
            if scores.get(c.id, 0) < 0.6
        ]
        low_scores.sort(key=lambda x: x[1])

        if not low_scores:
            return ""

        criteria_summary = "\n".join(
            f"- {c.name}: {score:.2f} ({c.description})"
            for c, score in low_scores[:3]
        )

        prompt = f"""Based on the evaluation scores below, provide brief improvement suggestions.

Query: {query}
Response: {response[:500]}

Low-scoring criteria:
{criteria_summary}

Provide 2-3 specific, actionable suggestions to improve the response.
Keep it concise (under 100 words)."""

        try:
            feedback = provider.generate(prompt, max_tokens=150)
            return feedback.strip()
        except Exception as e:
            print(f"[CriticEvaluator] Feedback generation failed: {e}")
            return self._heuristic_feedback(criteria, scores)

    def _heuristic_feedback(
        self,
        criteria: list[EvaluationCriterion],
        scores: dict[str, float],
    ) -> str:
        """Generate simple feedback without LLM."""
        low_criteria = [
            c.name for c in criteria if scores.get(c.id, 0) < 0.6
        ]
        if not low_criteria:
            return ""
        return f"Consider improving: {', '.join(low_criteria[:3])}"

    def save_to_neo4j(self, evaluation: Evaluation) -> bool:
        """Persist evaluation to Neo4j.

        Args:
            evaluation: Evaluation to save.

        Returns:
            True if successful, False otherwise.
        """
        try:
            settings = get_app_settings()
            client = Neo4jClient(
                uri=settings.neo4j_uri,
                username=settings.neo4j_username,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            )
            client.connect()

            query = """
            MERGE (e:Evaluation {id: $id})
            SET e.agent_name = $agent_name,
                e.query = $query,
                e.response = $response,
                e.scores = $scores,
                e.composite_score = $composite_score,
                e.feedback = $feedback,
                e.created_at = datetime($created_at),
                e.conversation_id = $conversation_id
            """

            client.run_cypher(
                query,
                {
                    "id": evaluation.id,
                    "agent_name": evaluation.agent_name,
                    "query": evaluation.query,
                    "response": evaluation.response,
                    "scores": json.dumps(evaluation.scores),
                    "composite_score": evaluation.composite_score,
                    "feedback": evaluation.feedback,
                    "created_at": evaluation.created_at.isoformat(),
                    "conversation_id": evaluation.conversation_id,
                },
            )

            # Create relationships to criteria used
            for criterion_id in evaluation.scores.keys():
                rel_query = """
                MATCH (e:Evaluation {id: $eval_id})
                MATCH (ec:EvaluationCriteria {id: $criterion_id})
                MERGE (e)-[:USES_CRITERIA {score: $score}]->(ec)
                """
                client.run_cypher(
                    rel_query,
                    {
                        "eval_id": evaluation.id,
                        "criterion_id": criterion_id,
                        "score": evaluation.scores[criterion_id],
                    },
                )

            client.close()
            return True

        except Exception as e:
            print(f"[CriticEvaluator] Failed to save evaluation: {e}")
            return False


# Singleton instance
_evaluator: Optional[CriticEvaluator] = None


def get_evaluator() -> CriticEvaluator:
    """Get or create the singleton CriticEvaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = CriticEvaluator()
    return _evaluator
