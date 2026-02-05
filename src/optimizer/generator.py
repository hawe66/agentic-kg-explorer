"""Variant Generator for creating prompt improvements."""

import json
import re
from datetime import datetime
from typing import Optional

from src.agents.providers.router import get_provider

from .models import FailurePattern, PromptVariant
from .registry import get_registry


class VariantGenerator:
    """Generate prompt variants to address failure patterns."""

    def __init__(self):
        self.registry = get_registry()
        self._variant_counter = 0

    def generate_variants(
        self,
        failure_pattern: FailurePattern,
        num_variants: int = 3,
    ) -> list[PromptVariant]:
        """Generate prompt variants addressing the failure.

        Args:
            failure_pattern: The pattern to address.
            num_variants: Number of variants to generate.

        Returns:
            List of PromptVariant objects.
        """
        # Load current prompt
        current_prompt = self._load_current_prompt(failure_pattern.agent_name)
        if not current_prompt:
            print(f"[VariantGenerator] No current prompt found for {failure_pattern.agent_name}")
            return []

        # Generate variants using LLM
        provider = get_provider()
        if provider is None:
            print("[VariantGenerator] No LLM provider available")
            return []

        variants = self._generate_with_llm(
            current_prompt,
            failure_pattern,
            num_variants,
            provider,
        )

        return variants

    def _load_current_prompt(self, agent_name: str) -> Optional[str]:
        """Load the current prompt for an agent."""
        # First try registry
        prompt = self.registry.load_prompt(agent_name)
        if prompt:
            return prompt

        # Fall back to extracting from code
        prompt = self._extract_prompt_from_code(agent_name)
        return prompt

    def _extract_prompt_from_code(self, agent_name: str) -> Optional[str]:
        """Extract prompt from agent code (fallback)."""
        from pathlib import Path

        agent_files = {
            "synthesizer": "src/agents/nodes/synthesizer.py",
            "intent_classifier": "src/agents/nodes/intent_classifier.py",
            "search_planner": "src/agents/nodes/search_planner.py",
            "graph_retriever": "src/agents/nodes/graph_retriever.py",
        }

        file_path = agent_files.get(agent_name)
        if not file_path:
            return None

        path = Path(__file__).parents[2] / file_path
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        # Look for prompt patterns (triple-quoted strings with prompt-like content)
        # This is a heuristic - prompts usually contain instructions
        patterns = [
            r'prompt\s*=\s*f?"""(.*?)"""',
            r'prompt\s*=\s*f?\'\'\'(.*?)\'\'\'',
            r'PROMPT\s*=\s*f?"""(.*?)"""',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()

        return None

    def _generate_with_llm(
        self,
        current_prompt: str,
        failure_pattern: FailurePattern,
        num_variants: int,
        provider,
    ) -> list[PromptVariant]:
        """Generate variants using LLM."""
        # Build the generation prompt
        hypotheses_text = "\n".join(
            f"- {h}" for h in failure_pattern.root_cause_hypotheses
        )

        samples_text = ""
        for i, q in enumerate(failure_pattern.sample_queries[:3]):
            samples_text += f"  {i+1}. {q}\n"

        generation_prompt = f"""You are a prompt engineer. Your task is to improve a prompt that has a recurring issue.

## Current Prompt for {failure_pattern.agent_name}:
---
{current_prompt[:2000]}
---

## Problem:
{failure_pattern.description}

Average score: {failure_pattern.avg_score:.2f} on criterion: {failure_pattern.criterion_id}

## Sample failing queries:
{samples_text}

## Root cause hypotheses:
{hypotheses_text}

## Task:
Generate {num_variants} improved versions of this prompt. Each version should:
1. Address at least one of the hypotheses above
2. Be a COMPLETE replacement prompt (not a diff)
3. Keep the same overall structure but improve the problematic areas
4. Include specific instructions or examples to fix the issue

Output as JSON:
[
  {{
    "prompt": "Full improved prompt text here...",
    "rationale": "Brief explanation of what was changed and why",
    "addresses_hypotheses": [0, 1]
  }},
  ...
]

Only output valid JSON, no other text."""

        try:
            response = provider.generate(generation_prompt, max_tokens=4000)

            # Parse JSON from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if not json_match:
                print("[VariantGenerator] Could not parse JSON from LLM response")
                return []

            variants_data = json.loads(json_match.group())
            variants = []

            for i, v in enumerate(variants_data[:num_variants]):
                self._variant_counter += 1
                variant = PromptVariant(
                    id=f"var:{failure_pattern.agent_name}:{self._variant_counter:03d}",
                    agent_name=failure_pattern.agent_name,
                    prompt_content=v.get("prompt", ""),
                    rationale=v.get("rationale", ""),
                    addresses_hypotheses=v.get("addresses_hypotheses", []),
                    failure_pattern_id=failure_pattern.id,
                )
                variants.append(variant)

            return variants

        except json.JSONDecodeError as e:
            print(f"[VariantGenerator] JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"[VariantGenerator] Generation failed: {e}")
            return []

    def generate_diff(self, original: str, modified: str) -> str:
        """Generate a simple diff between two prompts."""
        import difflib

        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile="current",
            tofile="proposed",
            lineterm="",
        )

        return "".join(diff)

    def apply_variant(
        self,
        variant: PromptVariant,
        test_results: dict = None,
        performance_delta: float = 0.0,
    ) -> str:
        """Create a new PromptVersion from a variant.

        Args:
            variant: The variant to apply.
            test_results: Test results summary.
            performance_delta: Performance improvement.

        Returns:
            New version ID.
        """
        pv = self.registry.create_version(
            agent_name=variant.agent_name,
            content=variant.prompt_content,
            rationale=variant.rationale,
            failure_pattern_id=variant.failure_pattern_id,
            test_results=test_results,
            performance_delta=performance_delta,
        )
        return pv.id
