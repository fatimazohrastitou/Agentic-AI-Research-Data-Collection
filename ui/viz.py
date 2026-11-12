"""Visualization helpers for the Streamlit UI (separate module to avoid stale imports)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from ui.helpers import (
    OUTPUTS,
    as_dataframe,
    completion_score,
    list_output_runs,
    part1_status,
    part2_status,
    read_json,
    read_text,
    run_dir,
    screening_summary,
)


def decision_chart_df(summary: dict[str, int], label: str = "decision") -> pd.DataFrame:
    rows = [{label: k, "n": int(v)} for k, v in (summary or {}).items()]
    if not rows:
        return pd.DataFrame(columns=[label, "n"])
    return pd.DataFrame(rows).sort_values("n", ascending=False)


def prisma_funnel_rows(prisma: dict) -> pd.DataFrame:
    steps = [
        ("Identifies", prisma.get("records_identified")),
        ("Apres deduplication", prisma.get("records_after_deduplication")),
        ("Screening titre/resume", prisma.get("records_screened_title_abstract")),
        ("Handoff / a revoir", prisma.get("needs_human_review")),
        ("Full-text evalues", prisma.get("fulltext_assessed")),
        ("Inclus (final draft)", prisma.get("records_included")),
    ]
    rows = []
    for label, value in steps:
        if value is None:
            continue
        rows.append({"etape": label, "n": int(value)})
    return pd.DataFrame(rows)


def load_run_bundle(folder: Path) -> dict[str, Any]:
    p2 = folder / "part2"
    return {
        "folder": folder,
        "protocol": read_json(folder / "research_protocol.json", {}),
        "strategy": read_json(folder / "search_strategy.json", {}),
        "prisma1": read_json(folder / "prisma_statistics.json", {}),
        "screening": read_json(folder / "screening_results.json", []),
        "handoff": read_json(folder / "part2_handoff.json", []),
        "fulltext": read_json(p2 / "fulltext_screening.json", []),
        "evidence": read_json(p2 / "evidence_table.json", []),
        "rob": read_json(p2 / "risk_of_bias.json", []),
        "rag_meta": read_json(p2 / "rag_index" / "meta.json", {}),
        "synthesis": read_json(p2 / "synthesis.json", {}),
        "critic": read_json(p2 / "critic_report.json", {}),
        "evaluation": read_json(p2 / "evaluation.json", {}),
        "prisma2": read_json(p2 / "prisma_reconciled.json", {}),
        "manuscript": read_text(p2 / "review_manuscript_draft.md"),
        "bib": read_text(p2 / "included_studies.bib"),
        "status1": part1_status(folder),
        "status2": part2_status(folder),
        "completion": completion_score(folder),
    }


__all__ = [
    "OUTPUTS",
    "as_dataframe",
    "decision_chart_df",
    "list_output_runs",
    "load_run_bundle",
    "prisma_funnel_rows",
    "run_dir",
    "screening_summary",
]
