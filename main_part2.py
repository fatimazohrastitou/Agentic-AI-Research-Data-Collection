"""CLI entry point for Part 2 — full-text screening, extraction, RAG synthesis, report."""
from __future__ import annotations

import argparse
from pathlib import Path

from workflow.part2_pipeline import run_part2_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Part 2 - Full-text screening, extraction, RoB, RAG synthesis and PRISMA report"
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Part 1 output folder containing part2_handoff.json (e.g. outputs/cybersecurity_in_iot)",
    )
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        raise SystemExit(f"Directory not found: {output_dir}")

    result = run_part2_pipeline(str(output_dir))
    stats = result.get("load_stats") or {}
    prisma = result.get("prisma") or {}
    critic = result.get("critic") or {}
    evaluation = result.get("evaluation") or {}

    print("\n=== PART 2 COMPLETED ===")
    print("Input folder:", output_dir.resolve())
    print("Part 2 artefacts:", result.get("part2_dir"))
    print("LLM mode:", stats.get("llm_mode"))
    print("Records loaded:", stats.get("n_records"))
    print("Human decisions applied:", stats.get("human_decisions_applied"))
    print("PDF parsed:", stats.get("records_pdf_parsed"))
    print("Full-text assessed:", prisma.get("fulltext_assessed"))
    print("Included:", prisma.get("records_included"))
    print("Extractions:", len(result.get("extractions") or []))
    print("Critic verdict:", critic.get("verdict"), f"(score {critic.get('quality_score')})")
    print("Evaluation completeness:", (evaluation.get("completeness") or {}))
    print("Manuscript:", Path(result.get("part2_dir", "")) / "review_manuscript_draft.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
