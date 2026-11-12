"""Simplified risk-of-bias / critical appraisal for included studies."""
from __future__ import annotations

import re
from typing import Any

from tools.llm_config import invoke_llm, llm_mode


DOMAINS = [
    ("selection_bias", ["random", "sampling", "selection", "inclusion criteria"]),
    ("performance_bias", ["blinding", "blinded", "allocation", "concealment"]),
    ("detection_bias", ["outcome assessment", "measurement", "validated", "instrument"]),
    ("attrition_bias", ["dropout", "attrition", "missing data", "lost to follow"]),
    ("reporting_bias", ["protocol", "pre-registered", "all outcomes", "selective"]),
    ("other_bias", ["conflict of interest", "funding", "limitation"]),
]


def _score_domain(text: str, keywords: list[str]) -> tuple[str, str]:
    low = text.lower()
    hits = [k for k in keywords if k in low]
    if len(hits) >= 2:
        return "low", "Multiple relevant methodological cues found: " + ", ".join(hits)
    if hits:
        return "unclear", "Limited cues found: " + ", ".join(hits)
    return "unclear", "Insufficient information in available text."


def _heuristic_rob(record: dict) -> dict[str, Any]:
    text = (record.get("full_text") or record.get("abstract") or "").lower()
    domains = {}
    judgements = []
    for name, keys in DOMAINS:
        judgement, reason = _score_domain(text, keys)
        domains[name] = {"judgement": judgement, "rationale": reason}
        judgements.append(judgement)

    if judgements.count("high") >= 2:
        overall = "high"
    elif judgements.count("low") >= 3 and "high" not in judgements:
        overall = "low"
    else:
        overall = "unclear"

    # Lightweight signals that often imply higher risk in poorly reported papers.
    if len(text) < 400:
        overall = "unclear"
        domains["reporting_bias"] = {
            "judgement": "unclear",
            "rationale": "Very short available text; reporting completeness cannot be assessed.",
        }

    return {
        "study_id": record.get("openalex_id") or record.get("doi") or record.get("title"),
        "title": record.get("title"),
        "year": record.get("year"),
        "tool": "simplified_domain_checklist_v1",
        "domains": domains,
        "overall_risk_of_bias": overall,
        "appraisal_method": "heuristic_keyword_domains_v1",
        "note": "Simplified checklist for transparency; not a full Cochrane RoB 2 appraisal.",
    }


def _llm_rob(record: dict) -> dict[str, Any] | None:
    text = (record.get("full_text") or record.get("abstract") or "")[:12000]
    if not text.strip():
        return None
    system = (
        "Perform a brief risk-of-bias appraisal. Reply with lines: "
        "OVERALL: <low|unclear|high> and one short RATIONALE."
    )
    user = f"Title: {record.get('title', '')}\nText:\n{text}"
    raw = invoke_llm(system, user)
    if not raw or raw.startswith("[llm_error]"):
        return None
    base = _heuristic_rob(record)
    m = re.search(r"OVERALL:\s*(low|unclear|high)", raw, re.I)
    if m:
        base["overall_risk_of_bias"] = m.group(1).lower()
    rationale = re.search(r"RATIONALE:\s*(.+)", raw, re.I | re.S)
    if rationale:
        base["llm_rationale"] = rationale.group(1).strip().splitlines()[0][:500]
    base["appraisal_method"] = f"llm_{llm_mode()}_plus_heuristic"
    return base


def appraise_risk_of_bias(records: list[dict]) -> list[dict]:
    included = [r for r in records if r.get("included_for_extraction")]
    rows = []
    for record in included:
        rows.append(_llm_rob(record) or _heuristic_rob(record))
    return rows
