"""CLI tool for analyzing failure patterns.

Usage:
    poetry run python scripts/analyze_failures.py
    poetry run python scripts/analyze_failures.py --agent synthesizer
    poetry run python scripts/analyze_failures.py --threshold 0.5
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.optimizer.analyzer import FailureAnalyzer


def main():
    parser = argparse.ArgumentParser(description="Analyze failure patterns from evaluations")
    parser.add_argument(
        "--agent",
        help="Filter by agent name (e.g., synthesizer)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Score threshold for failures (default: 0.6)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=5,
        help="Minimum samples to create pattern (default: 5)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing patterns instead of analyzing",
    )
    parser.add_argument(
        "--status",
        help="Filter existing patterns by status",
    )

    args = parser.parse_args()

    analyzer = FailureAnalyzer(
        threshold=args.threshold,
        min_samples=args.min_samples,
    )

    if args.list:
        # List existing patterns
        print("\n" + "=" * 60)
        print("Existing Failure Patterns")
        print("=" * 60)

        patterns = analyzer.get_patterns(status=args.status, agent_name=args.agent)

        if not patterns:
            print("\nNo failure patterns found.")
            return 0

        for fp in patterns:
            print(f"\n[{fp.status.upper()}] {fp.id}")
            print(f"  Agent: {fp.agent_name}")
            print(f"  Criterion: {fp.criterion_id}")
            print(f"  Frequency: {fp.frequency}")
            print(f"  Avg Score: {fp.avg_score:.2f}")
            print(f"  Description: {fp.description}")
            if fp.root_cause_hypotheses:
                print("  Hypotheses:")
                for h in fp.root_cause_hypotheses:
                    print(f"    - {h}")

        print(f"\nTotal: {len(patterns)} patterns")
        return 0

    # Analyze evaluations
    print("\n" + "=" * 60)
    print("Failure Pattern Analysis")
    print("=" * 60)
    print(f"\nSettings:")
    print(f"  Threshold: {args.threshold}")
    print(f"  Min samples: {args.min_samples}")
    if args.agent:
        print(f"  Agent filter: {args.agent}")

    print("\nAnalyzing evaluations...")
    patterns = analyzer.analyze(agent_name=args.agent)

    if not patterns:
        print("\nNo failure patterns detected.")
        print("This could mean:")
        print("  - Not enough low-scoring evaluations (need >= 5)")
        print("  - No evaluations in the database yet")
        print("  - All scores are above threshold")
        return 0

    print(f"\nDetected {len(patterns)} failure pattern(s):")

    for fp in patterns:
        print(f"\n{'─' * 50}")
        print(f"Pattern: {fp.id}")
        print(f"  Agent: {fp.agent_name}")
        print(f"  Criterion: {fp.criterion_id}")
        print(f"  Type: {fp.pattern_type}")
        print(f"  Frequency: {fp.frequency} failures")
        print(f"  Avg Score: {fp.avg_score:.2f}")
        print(f"\n  Description: {fp.description}")

        print("\n  Sample Queries:")
        for q in fp.sample_queries[:3]:
            print(f"    - {q[:60]}...")

        print("\n  Root Cause Hypotheses:")
        for i, h in enumerate(fp.root_cause_hypotheses):
            print(f"    {i+1}. {h}")

    print(f"\n{'=' * 60}")
    print("Next Steps:")
    print("  1. Review hypotheses in Streamlit UI")
    print("  2. Run: poetry run python scripts/generate_variants.py --pattern <id>")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
