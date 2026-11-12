"""Load Part 1 artefacts and prepare records for the Part 2 pipeline."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from tools.pdf_parser import extract_pdf_sections


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _doi_key(value: str) -> str:
    value = str(value or "").strip().lower()
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return value


def load_human_decisions(xlsx_path: Path) -> dict[str, dict[str, str]]:
    """Map DOI / title -> human decision fields from human_review.xlsx."""
    if not xlsx_path.is_file():
        return {}
    df = pd.read_excel(xlsx_path)
    mapping: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        decision = str(row.get("Human decision (fill in)", "") or "").strip()
        notes = str(row.get("Reviewer notes", "") or "").strip()
        if not decision and not notes:
            continue
        payload = {
            "human_decision": decision,
            "reviewer_notes": notes,
        }
        doi = _doi_key(row.get("DOI", ""))
        title = _norm_key(row.get("Title", ""))
        if doi:
            mapping[f"doi:{doi}"] = payload
        if title:
            mapping[f"title:{title}"] = payload
    return mapping


def apply_human_decisions(records: list[dict], decisions: dict[str, dict[str, str]]) -> list[dict]:
    enriched = []
    for item in records:
        row = dict(item)
        doi = _doi_key(row.get("doi", ""))
        title = _norm_key(row.get("title", ""))
        hit = None
        if doi and f"doi:{doi}" in decisions:
            hit = decisions[f"doi:{doi}"]
        elif title and f"title:{title}" in decisions:
            hit = decisions[f"title:{title}"]
        if hit:
            row["human_decision"] = hit.get("human_decision", "")
            row["reviewer_notes"] = hit.get("reviewer_notes", "")
        else:
            row.setdefault("human_decision", "")
            row.setdefault("reviewer_notes", "")
        enriched.append(row)
    return enriched


def _attach_pdf_text(record: dict, output_dir: Path) -> dict:
    row = dict(record)
    if (row.get("full_text") or "").strip() and row.get("pdf_parse_status") == "parsed":
        return row

    candidates: list[Path] = []
    local = row.get("local_pdf_path")
    if local:
        candidates.append(Path(local))
        candidates.append(output_dir / "full_texts" / Path(local).name)
    openalex_id = str(row.get("openalex_id") or "").split("/")[-1]
    if openalex_id:
        ft = output_dir / "full_texts"
        if ft.is_dir():
            for path in ft.glob(f"*{openalex_id}*.pdf"):
                candidates.append(path)

    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()).lower() if path.exists() else str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        if not path.is_file():
            continue
        try:
            parsed = extract_pdf_sections(path)
            full_text = (parsed.get("full_text") or "").strip()
            if not full_text:
                continue
            row["local_pdf_path"] = str(path)
            row["full_text"] = full_text
            row["sections"] = parsed.get("sections", {})
            row["detected_headings"] = parsed.get("detected_headings", [])
            row["structure_warnings"] = parsed.get("structure_warnings", [])
            row["pdf_page_count"] = parsed.get("page_count", 0)
            row["pdf_character_count"] = parsed.get("character_count", 0)
            row["pdf_parse_status"] = "parsed"
            return row
        except Exception as exc:
            row["pdf_parse_status"] = "parse_failed"
            row["pdf_parse_error"] = f"{type(exc).__name__}: {exc}"
    if not (row.get("full_text") or "").strip():
        # Fall back to abstract-only corpus for RAG / screening when PDF missing.
        abstract = (row.get("abstract") or "").strip()
        row.setdefault("pdf_parse_status", "abstract_only" if abstract else "no_text")
        row["full_text"] = abstract
        row.setdefault("sections", {"abstract": {"text": abstract}} if abstract else {})
    return row


def load_part2_inputs(output_dir: str | Path) -> dict[str, Any]:
    """Load protocol, handoff, human decisions, PRISMA stats and enrich texts."""
    base = Path(output_dir)
    if not base.is_dir():
        raise FileNotFoundError(f"Part 1 output directory not found: {base}")

    handoff_path = base / "part2_handoff.json"
    if not handoff_path.is_file():
        raise FileNotFoundError(
            f"Missing {handoff_path}. Run Part 1 first (python main.py ...)."
        )

    records = read_json(handoff_path, [])
    if not isinstance(records, list):
        raise TypeError("part2_handoff.json must contain a JSON list")

    protocol = read_json(base / "research_protocol.json", {})
    prisma = read_json(base / "prisma_statistics.json", {})
    decisions = load_human_decisions(base / "human_review.xlsx")
    records = apply_human_decisions(records, decisions)
    records = [_attach_pdf_text(r, base) for r in records]

    return {
        "output_dir": str(base.resolve()),
        "protocol": protocol or {},
        "prisma_part1": prisma or {},
        "records": records,
        "human_decisions_applied": sum(1 for r in records if r.get("human_decision")),
        "records_with_full_text": sum(1 for r in records if (r.get("full_text") or "").strip()),
        "records_pdf_parsed": sum(1 for r in records if r.get("pdf_parse_status") == "parsed"),
    }
