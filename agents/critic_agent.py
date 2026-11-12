"""Critic / QA agent: checks consistency, completeness and protocol adherence."""
from __future__ import annotations

from typing import Any

from tools.llm_config import invoke_llm, llm_mode


def _heuristic_critique(
    protocol: dict,
    screened: list[dict],
    extractions: list[dict],
    rob: list[dict],
    synthesis: dict,
    prisma: dict,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    warnings: list[str] = []

    included = [r for r in screened if r.get("fulltext_decision") == "include"]
    if len(included) != len(extractions):
        issues.append({
            "severity": "high",
            "code": "extraction_count_mismatch",
            "message": (
                f"Included studies ({len(included)}) != extraction rows ({len(extractions)})."
            ),
        })

    if len(rob) != len(extractions):
        issues.append({
            "severity": "medium",
            "code": "rob_count_mismatch",
            "message": f"RoB rows ({len(rob)}) != extraction rows ({len(extractions)}).",
        })

    human_final = sum(1 for r in screened if r.get("fulltext_is_final"))
    if human_final == 0 and screened:
        warnings.append(
            "No final human Include/Exclude decisions found; automated full-text decisions remain preliminary."
        )

    missing_text = sum(1 for r in included if not (r.get("full_text") or "").strip())
    if missing_text:
        warnings.append(f"{missing_text} included study(ies) lack usable full text.")

    if not protocol.get("inclusion_criteria") and not protocol.get("exclusion_criteria"):
        warnings.append("Protocol has empty inclusion/exclusion criteria lists.")

    if synthesis.get("n_included", 0) == 0:
        issues.append({
            "severity": "high",
            "code": "empty_synthesis",
            "message": "Synthesis has zero included studies.",
        })

    if prisma.get("records_included") is None:
        warnings.append("PRISMA included count missing before critic pass.")

    citations = synthesis.get("citations") or []
    if extractions and not citations:
        issues.append({
            "severity": "medium",
            "code": "missing_citations",
            "message": "Synthesis citations list is empty despite extractions.",
        })

    score = 100
    score -= 15 * sum(1 for i in issues if i["severity"] == "high")
    score -= 8 * sum(1 for i in issues if i["severity"] == "medium")
    score -= 3 * len(warnings)
    score = max(0, min(100, score))

    verdict = "pass" if score >= 80 and not any(i["severity"] == "high" for i in issues) else (
        "pass_with_warnings" if score >= 60 else "needs_revision"
    )

    return {
        "verdict": verdict,
        "quality_score": score,
        "issues": issues,
        "warnings": warnings,
        "checks": {
            "n_screened_fulltext": len(screened),
            "n_included": len(included),
            "n_extractions": len(extractions),
            "n_rob": len(rob),
            "human_final_decisions": human_final,
            "synthesis_method": synthesis.get("synthesis_method"),
            "llm_mode_note": llm_mode(),
        },
        "critic_method": "heuristic_consistency_v1",
        "recommendation": (
            "Address high-severity issues and complete human screening before treating "
            "the manuscript draft as submission-ready."
        ),
    }


def critique_outputs(
    protocol: dict,
    screened: list[dict],
    extractions: list[dict],
    rob: list[dict],
    synthesis: dict,
    prisma: dict,
) -> dict[str, Any]:
    base = _heuristic_critique(protocol, screened, extractions, rob, synthesis, prisma)
    system = (
        "You are a systematic-review QA critic. Given a JSON-like summary, reply with "
        "VERDICT: pass|pass_with_warnings|needs_revision and 3 short bullet issues max."
    )
    user = (
        f"Topic: {protocol.get('topic')}\n"
        f"Included: {base['checks']['n_included']}\n"
        f"Extractions: {base['checks']['n_extractions']}\n"
        f"Heuristic verdict: {base['verdict']}\n"
        f"Issues: {base['issues']}\n"
        f"Warnings: {base['warnings']}"
    )
    raw = invoke_llm(system, user)
    if raw and not raw.startswith("[llm_error]"):
        base["llm_commentary"] = raw[:1500]
        base["critic_method"] = f"heuristic_plus_llm_{llm_mode()}"
    return base
