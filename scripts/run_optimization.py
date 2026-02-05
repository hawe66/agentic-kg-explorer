"""CLI tool for running the full optimization pipeline.

Usage:
    poetry run python scripts/run_optimization.py --agent synthesizer
    poetry run python scripts/run_optimization.py --pattern fp:synthesizer:source-citation:2026-02
    poetry run python scripts/run_optimization.py --agent synthesizer --auto-approve
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.optimizer.analyzer import FailureAnalyzer, get_analyzer
from src.optimizer.generator import VariantGenerator
from src.optimizer.runner import TestRunner
from src.optimizer.registry import get_registry


def main():
    parser = argparse.ArgumentParser(description="Run prompt optimization pipeline")
    parser.add_argument(
        "--agent",
        help="Agent to optimize (e.g., synthesizer)",
    )
    parser.add_argument(
        "--pattern",
        help="Specific failure pattern ID to address",
    )
    parser.add_argument(
        "--num-variants",
        type=int,
        default=3,
        help="Number of variants to generate (default: 3)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve best variant without confirmation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    if not args.agent and not args.pattern:
        parser.error("Either --agent or --pattern is required")

    analyzer = get_analyzer()
    generator = VariantGenerator()
    runner = TestRunner()
    registry = get_registry()

    # Step 1: Get or detect failure pattern
    print("\n" + "=" * 60)
    print("STEP 1: Failure Pattern")
    print("=" * 60)

    if args.pattern:
        # Load specific pattern
        patterns = analyzer.get_patterns()
        pattern = next((p for p in patterns if p.id == args.pattern), None)
        if not pattern:
            print(f"Pattern not found: {args.pattern}")
            return 1
    else:
        # Detect patterns for agent
        patterns = analyzer.analyze(agent_name=args.agent)
        if not patterns:
            print(f"No failure patterns detected for {args.agent}")
            print("Run some queries with evaluation enabled first.")
            return 1
        pattern = patterns[0]  # Take the first/worst pattern

    print(f"\nPattern: {pattern.id}")
    print(f"  Agent: {pattern.agent_name}")
    print(f"  Criterion: {pattern.criterion_id}")
    print(f"  Frequency: {pattern.frequency}")
    print(f"  Avg Score: {pattern.avg_score:.2f}")

    print("\n  Hypotheses:")
    for i, h in enumerate(pattern.root_cause_hypotheses):
        print(f"    {i+1}. {h}")

    # Gate 1: Confirm hypotheses
    if not args.auto_approve and not args.dry_run:
        print("\n[Gate 1] Do you want to proceed with these hypotheses? (y/n): ", end="")
        response = input().strip().lower()
        if response not in ("y", "yes"):
            print("Aborted.")
            return 0

    # Step 2: Generate variants
    print("\n" + "=" * 60)
    print("STEP 2: Generate Variants")
    print("=" * 60)

    if args.dry_run:
        print(f"\n[DRY RUN] Would generate {args.num_variants} variants")
        variants = []
    else:
        print(f"\nGenerating {args.num_variants} prompt variants...")
        variants = generator.generate_variants(pattern, num_variants=args.num_variants)

        if not variants:
            print("Failed to generate variants")
            return 1

        for i, v in enumerate(variants):
            print(f"\nVariant {i+1}: {v.id}")
            print(f"  Rationale: {v.rationale}")
            print(f"  Addresses hypotheses: {v.addresses_hypotheses}")
            print(f"  Prompt length: {len(v.prompt_content)} chars")

    # Step 3: Run tests
    print("\n" + "=" * 60)
    print("STEP 3: Test Variants")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Would run test suite against variants")
        results = []
    elif variants:
        print("\nRunning test suite...")
        results = runner.run_tests(pattern.agent_name, variants)

        print("\nTest Results (ranked by improvement):")
        for i, r in enumerate(results):
            print(f"\n  {i+1}. {r.variant.id}")
            print(f"     Performance Delta: {r.performance_delta:+.2%}")
            print(f"     Pass Rate: {r.pass_rate:.0%} ({r.passed_count}/{r.test_queries_count})")
            print(f"     Rationale: {r.variant.rationale[:60]}...")
    else:
        results = []

    # Step 4: Approve best variant
    print("\n" + "=" * 60)
    print("STEP 4: Approval")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Would prompt for approval of best variant")
        return 0

    if not results:
        print("\nNo test results to approve")
        return 1

    best = results[0]

    if best.performance_delta <= 0:
        print(f"\nBest variant shows no improvement ({best.performance_delta:+.2%})")
        print("Consider reviewing hypotheses or trying different approaches.")
        return 0

    print(f"\nBest variant: {best.variant.id}")
    print(f"  Improvement: {best.performance_delta:+.2%}")
    print(f"  Pass rate: {best.pass_rate:.0%}")

    # Show diff
    current_prompt = registry.load_prompt(pattern.agent_name) or ""
    if current_prompt:
        print("\n  Diff preview (first 500 chars of new prompt):")
        print("  " + "-" * 40)
        print(f"  {best.variant.prompt_content[:500]}...")

    # Gate 2: Confirm activation
    if not args.auto_approve:
        print("\n[Gate 2] Activate this variant? (y/n): ", end="")
        response = input().strip().lower()
        if response not in ("y", "yes"):
            print("Aborted. Variant saved but not activated.")
            # Still save the variant
            version_id = generator.apply_variant(
                best.variant,
                test_results={"pass_rate": best.pass_rate, "delta": best.performance_delta},
                performance_delta=best.performance_delta,
            )
            print(f"Saved as: {version_id}")
            return 0

    # Create and activate version
    version_id = generator.apply_variant(
        best.variant,
        test_results={"pass_rate": best.pass_rate, "delta": best.performance_delta},
        performance_delta=best.performance_delta,
    )
    print(f"\nCreated version: {version_id}")

    registry.activate_version(version_id, approved_by="cli")
    print(f"Activated: {version_id}")

    # Update pattern status
    analyzer.update_pattern_status(pattern.id, "resolved")
    print(f"Pattern marked as resolved: {pattern.id}")

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"\nNew prompt version {version_id} is now active.")
    print("Run queries to verify the improvement.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
