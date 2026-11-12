"""Full-text eligibility screening for Part 2.

Respects human decisions from human_review.xlsx when present.
Automated decisions remain preliminary unless a human Include/Exclude is supplied.
"""
from __future__ import annotations

import re

from tools.llm_config import invoke_llm, llm_mode


def _norm_terms(terms):
    return [str(t).strip().lower() for t in (terms or []) if str(t).strip()]


def _hits(text: str, terms: list[str]) -> list[str]:
    text = (text or "").lower()
    return [t for t in terms if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text)]


def _heuristic_decision(record: dict, include_terms: list[str], exclude_terms: list[str]) -> tuple[str, str]:
    human = str(record.get("human_decision") or "").strip().lower()
    if human == "include":
        return "include", "Human reviewer marked Include in human_review.xlsx."
    if human == "exclude":
        return "exclude", "Human reviewer marked Exclude in human_review.xlsx."
    if human == "unclear":
        return "uncertain", "Human reviewer marked Unclear; retained for discussion."

    text = (record.get("full_text") or record.get("abstract") or "").strip()
    if not text:
        return "uncertain", "No full text or abstract available for eligibility assessment."

    exclude_hits = _hits(text, exclude_terms)
    include_hits = _hits(text, include_terms)
    if exclude_hits:
        return "exclude", "Full-text exclusion term(s) matched: " + ", ".join(exclude_hits)
    if include_terms and include_hits:
        return "include", "Full-text inclusion term(s) matched: " + ", ".join(include_hits)
    if include_terms:
        return "uncertain", "No inclusion terms matched in available text; human confirmation required."
    # No criteria: keep potentially_include / uncertain from Part 1 as provisional include candidates.
    prior = record.get("title_abstract_decision")
    if prior == "potentially_include":
        return "include", "No explicit criteria; provisional include based on Part 1 potentially_include."
    return "uncertain", "No explicit criteria and weak Part 1 signal; human full-text review required."


def _llm_decision(record: dict, protocol: dict) -> tuple[str, str] | None:
    text = (record.get("full_text") or record.get("abstract") or "")[:12000]
    if not text.strip():
        return None
    system = (
        "You are a systematic review screener following PRISMA. "
        "Decide include, exclude, or uncertain for one study. "
        "Reply EXACTLY in the form: DECISION: <include|exclude|uncertain>\\nREASON: <one sentence>."
    )
    user = (
        f"Topic: {protocol.get('topic', '')}\n"
        f"Question: {protocol.get('research_question', '')}\n"
        f"Inclusion criteria: {protocol.get('inclusion_criteria', [])}\n"
        f"Exclusion criteria: {protocol.get('exclusion_criteria', [])}\n"
        f"Title: {record.get('title', '')}\n"
        f"Text:\n{text}"
    )
    raw = invoke_llm(system, user)
    if not raw or raw.startswith("[llm_error]"):
        return None
    decision_match = re.search(r"DECISION:\s*(include|exclude|uncertain)", raw, re.I)
    reason_match = re.search(r"REASON:\s*(.+)", raw, re.I | re.S)
    if not decision_match:
        return None
    decision = decision_match.group(1).lower()
    reason = (reason_match.group(1).strip().splitlines()[0] if reason_match else raw[:300])
    return decision, f"LLM ({llm_mode()}): {reason}"


def screen_fulltext(records: list[dict], protocol: dict | None = None) -> list[dict]:
    protocol = protocol or {}
    include_terms = _norm_terms(protocol.get("inclusion_criteria"))
    exclude_terms = _norm_terms(protocol.get("exclusion_criteria"))
    screened = []
    for record in records:
        row = dict(record)
        # Human decisions always win.
        human = str(row.get("human_decision") or "").strip().lower()
        if human in {"include", "exclude", "unclear"}:
            decision, reason = _heuristic_decision(row, include_terms, exclude_terms)
            method = "human_review_xlsx"
        else:
            llm_result = _llm_decision(row, protocol)
            if llm_result:
                decision, reason = llm_result
                method = f"llm_{llm_mode()}"
            else:
                decision, reason = _heuristic_decision(row, include_terms, exclude_terms)
                method = "heuristic_fulltext_v1"

        row.update({
            "fulltext_decision": decision,
            "fulltext_reason": reason,
            "fulltext_screening_method": method,
            "fulltext_is_final": method == "human_review_xlsx" and human in {"include", "exclude"},
            "included_for_extraction": decision == "include",
        })
        screened.append(row)
    return screened
