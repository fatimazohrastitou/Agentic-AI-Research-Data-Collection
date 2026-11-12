"""Helpers for the Streamlit UI: load Part 1 / Part 2 artefacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def list_output_runs() -> list[str]:
    if not OUTPUTS.is_dir():
        return []
    runs: list[str] = []
    for path in sorted(OUTPUTS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not path.is_dir():
            continue
        if (
            (path / "part2_handoff.json").exists()
            or (path / "prisma_statistics.json").exists()
            or any(path.glob("*.json"))
        ):
            runs.append(path.name)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in runs:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def run_dir(name: str) -> Path:
    return OUTPUTS / name


def read_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_text(path: Path, default: str = "") -> str:
    if not path.is_file():
        return default
    return path.read_text(encoding="utf-8")


def as_dataframe(records: list[dict] | None, columns: list[str] | None = None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns or [])
    df = pd.DataFrame(records)
    if columns:
        keep = [c for c in columns if c in df.columns]
        return df[keep]
    return df


def screening_summary(records: list[dict], decision_key: str = "title_abstract_decision") -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in records or []:
        key = str(row.get(decision_key) or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def part1_status(folder: Path) -> dict[str, bool]:
    return {
        "protocol": (folder / "research_protocol.json").is_file(),
        "strategy": (folder / "search_strategy.json").is_file(),
        "articles": (folder / "articles.json").is_file() or (folder / "articles_raw.json").is_file(),
        "screening": (folder / "screening_results.json").is_file(),
        "handoff": (folder / "part2_handoff.json").is_file(),
        "prisma": (folder / "prisma_statistics.json").is_file(),
        "human_review": (folder / "human_review.xlsx").is_file(),
    }


def part2_status(folder: Path) -> dict[str, bool]:
    p2 = folder / "part2"
    return {
        "fulltext": (p2 / "fulltext_screening.json").is_file(),
        "evidence": (p2 / "evidence_table.json").is_file(),
        "rob": (p2 / "risk_of_bias.json").is_file(),
        "synthesis": (p2 / "synthesis.json").is_file(),
        "critic": (p2 / "critic_report.json").is_file(),
        "prisma": (p2 / "prisma_reconciled.json").is_file(),
        "evaluation": (p2 / "evaluation.json").is_file(),
        "manuscript": (p2 / "review_manuscript_draft.md").is_file(),
        "rag": (p2 / "rag_index" / "meta.json").is_file(),
    }


def completion_score(folder: Path) -> int:
    s1 = part1_status(folder)
    s2 = part2_status(folder)
    checks = list(s1.values()) + list(s2.values())
    if not checks:
        return 0
    return int(round(100 * sum(1 for x in checks if x) / len(checks)))


def prisma_funnel_rows(prisma: dict) -> pd.DataFrame:
    """Build a funnel-friendly table from reconciled / Part 1 PRISMA stats."""
    steps = [
        ("Identifiés", prisma.get("records_identified")),
        ("Après déduplication", prisma.get("records_after_deduplication")),
        ("Screening titre/résumé", prisma.get("records_screened_title_abstract")),
        ("Handoff / à revoir", prisma.get("needs_human_review")),
        ("Full-text évalués", prisma.get("fulltext_assessed")),
        ("Inclus (final draft)", prisma.get("records_included")),
    ]
    rows = []
    for label, value in steps:
        if value is None:
            continue
        rows.append({"étape": label, "n": int(value)})
    return pd.DataFrame(rows)


def decision_chart_df(summary: dict[str, int], label: str = "decision") -> pd.DataFrame:
    """Convert a decision->count mapping into a chart-friendly DataFrame."""
    rows = [{label: k, "n": int(v)} for k, v in (summary or {}).items()]
    if not rows:
        return pd.DataFrame(columns=[label, "n"])
    return pd.DataFrame(rows).sort_values("n", ascending=False)


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

