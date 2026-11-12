"""Narrative synthesis grounded on extracted evidence and RAG passages."""
from __future__ import annotations

from typing import Any

from tools.llm_config import invoke_llm, llm_mode
from tools.rag_store import retrieve_context


def _format_citations(extractions: list[dict]) -> list[str]:
    cites = []
    for row in extractions:
        authors = row.get("authors") or []
        lead = authors[0] if authors else "Unknown"
        if isinstance(lead, dict):
            lead = lead.get("display_name") or lead.get("name") or "Unknown"
        year = row.get("year") or "n.d."
        cites.append(f"{lead} et al., {year}" if authors else f"{row.get('title', 'Untitled')[:60]} ({year})")
    return cites


def _heuristic_synthesis(
    protocol: dict,
    extractions: list[dict],
    rob: list[dict],
    rag_hits: list[dict],
) -> dict[str, Any]:
    topic = protocol.get("topic", "the review topic")
    question = protocol.get("research_question", "")
    cites = _format_citations(extractions)
    findings = []
    for row in extractions[:12]:
        findings.append(
            f"- {row.get('title', 'Untitled')} ({row.get('year', 'n.d.')}): "
            f"{(row.get('key_findings') or '')[:220]}"
        )
    rob_summary = {
        "low": sum(1 for r in rob if r.get("overall_risk_of_bias") == "low"),
        "unclear": sum(1 for r in rob if r.get("overall_risk_of_bias") == "unclear"),
        "high": sum(1 for r in rob if r.get("overall_risk_of_bias") == "high"),
    }
    rag_block = "\n".join(
        f"- [{h.get('score')}] {h.get('title', '')}: {(h.get('text') or '')[:220]}"
        for h in rag_hits[:6]
    )
    narrative = (
        f"## Narrative synthesis\n\n"
        f"This draft synthesises {len(extractions)} included study(ies) on **{topic}**.\n"
        f"Review question: {question}\n\n"
        f"### Main findings\n"
        + ("\n".join(findings) if findings else "_No included studies available for synthesis._")
        + "\n\n### Risk-of-bias overview\n"
        f"- Low: {rob_summary['low']}; Unclear: {rob_summary['unclear']}; High: {rob_summary['high']}\n\n"
        "### Grounded passages (RAG)\n"
        + (rag_block or "_No RAG passages retrieved._")
        + "\n\n### Interpretation\n"
        "Evidence patterns above are organised thematically from extracted outcomes and retrieved "
        "passages. Automated synthesis is a draft aid; authors must verify citations, effect "
        "direction, and study eligibility before publication.\n"
    )
    return {
        "topic": topic,
        "research_question": question,
        "n_included": len(extractions),
        "citations": cites,
        "risk_of_bias_summary": rob_summary,
        "rag_passages_used": rag_hits[:8],
        "narrative_markdown": narrative,
        "synthesis_method": "heuristic_rag_template_v1",
        "meta_analysis_ready": False,
        "meta_analysis_note": (
            "Quantitative pooling was not performed automatically. "
            "Extracted outcomes can seed a manual meta-analysis if comparable effect measures exist."
        ),
    }


def _llm_synthesis(protocol: dict, extractions: list[dict], rag_hits: list[dict], base: dict) -> dict | None:
    if not extractions:
        return None
    evidence = "\n".join(
        f"- {e.get('title')} | design={e.get('study_design')} | findings={e.get('key_findings')}"
        for e in extractions[:20]
    )
    passages = "\n".join(
        f"- ({h.get('title')}) {h.get('text')}" for h in rag_hits[:8]
    )
    system = (
        "Write a concise PRISMA-oriented narrative synthesis in Markdown with sections: "
        "Main findings, Agreements/disagreements, Limitations, Implications. "
        "Cite study titles inline. Do not invent statistics."
    )
    user = (
        f"Topic: {protocol.get('topic')}\nQuestion: {protocol.get('research_question')}\n"
        f"Evidence table:\n{evidence}\n\nRetrieved passages:\n{passages}"
    )
    raw = invoke_llm(system, user, temperature=0.2)
    if not raw or raw.startswith("[llm_error]"):
        return None
    out = dict(base)
    out["narrative_markdown"] = raw
    out["synthesis_method"] = f"llm_{llm_mode()}_rag_grounded"
    return out


def synthesise_evidence(
    protocol: dict,
    extractions: list[dict],
    rob_rows: list[dict],
    rag_dir: str,
    query: str | None = None,
) -> dict[str, Any]:
    query = query or protocol.get("research_question") or protocol.get("topic") or ""
    rag_hits = retrieve_context(rag_dir, query, top_k=8) if rag_dir else []
    base = _heuristic_synthesis(protocol, extractions, rob_rows, rag_hits)
    return _llm_synthesis(protocol, extractions, rag_hits, base) or base
