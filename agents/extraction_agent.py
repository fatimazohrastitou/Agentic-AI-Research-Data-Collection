"""Structured data extraction for included studies."""
from __future__ import annotations

import json
import re
from typing import Any

from tools.llm_config import invoke_llm, llm_mode


def _section_text(record: dict, name: str) -> str:
    sections = record.get("sections") or {}
    value = sections.get(name)
    if isinstance(value, dict):
        return value.get("text") or ""
    return str(value or "")


def _heuristic_extract(record: dict, protocol: dict) -> dict[str, Any]:
    abstract = (record.get("abstract") or "").strip()
    methods = _section_text(record, "methodology") or _section_text(record, "methods")
    results = _section_text(record, "results")
    conclusion = _section_text(record, "conclusion")
    text = (record.get("full_text") or abstract)[:5000]

    population = ""
    for pattern in [
        r"(?:participants?|patients?|subjects?|sample)\s+(?:of\s+)?(\d[\d,\.]*)",
        r"n\s*=\s*(\d[\d,\.]*)",
    ]:
        m = re.search(pattern, text, re.I)
        if m:
            population = m.group(0)
            break

    design_hints = []
    for label, terms in {
        "randomized": ["randomised", "randomized", "rct"],
        "observational": ["cohort", "case-control", "cross-sectional", "observational"],
        "review": ["systematic review", "meta-analysis", "literature review"],
        "experimental": ["experiment", "prototype", "simulation", "benchmark"],
    }.items():
        if any(t in text.lower() for t in terms):
            design_hints.append(label)

    return {
        "study_id": record.get("openalex_id") or record.get("doi") or record.get("title"),
        "title": record.get("title"),
        "year": record.get("year"),
        "authors": record.get("authors") or [],
        "doi": record.get("doi"),
        "publication_type": record.get("type"),
        "research_question_addressed": protocol.get("research_question", ""),
        "study_design": ", ".join(design_hints) or "not clearly identified",
        "population_or_corpus": population or "not clearly reported in available text",
        "intervention_or_exposure": "see methods/results excerpts",
        "comparator": "not clearly reported",
        "outcomes": (results[:400] if results else abstract[:400]) or "not extracted",
        "key_findings": (conclusion[:500] if conclusion else abstract[:500]) or "not extracted",
        "methods_excerpt": (methods[:600] if methods else abstract[:600]),
        "limitations_noted": "Check discussion/limitations manually.",
        "extraction_method": "heuristic_section_regex_v1",
        "extraction_confidence": "low" if not methods and not results else "medium",
    }


def _llm_extract(record: dict, protocol: dict) -> dict[str, Any] | None:
    text = (record.get("full_text") or record.get("abstract") or "")[:14000]
    if not text.strip():
        return None
    system = (
        "Extract structured systematic-review evidence fields as compact JSON with keys: "
        "study_design, population_or_corpus, intervention_or_exposure, comparator, outcomes, "
        "key_findings, limitations_noted. Use short strings. If unknown, write 'not reported'."
    )
    user = (
        f"Review topic: {protocol.get('topic', '')}\n"
        f"Question: {protocol.get('research_question', '')}\n"
        f"Title: {record.get('title', '')}\n"
        f"Year: {record.get('year', '')}\n"
        f"Text:\n{text}"
    )
    raw = invoke_llm(system, user)
    if not raw or raw.startswith("[llm_error]"):
        return None
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    base = _heuristic_extract(record, protocol)
    base.update({k: data.get(k, base.get(k)) for k in [
        "study_design", "population_or_corpus", "intervention_or_exposure",
        "comparator", "outcomes", "key_findings", "limitations_noted",
    ]})
    base["extraction_method"] = f"llm_{llm_mode()}"
    base["extraction_confidence"] = "medium-high"
    return base


def extract_evidence(records: list[dict], protocol: dict | None = None) -> list[dict]:
    """Extract structured fields from studies marked included_for_extraction."""
    protocol = protocol or {}
    included = [r for r in records if r.get("included_for_extraction")]
    rows = []
    for record in included:
        llm_row = _llm_extract(record, protocol)
        rows.append(llm_row or _heuristic_extract(record, protocol))
    return rows
