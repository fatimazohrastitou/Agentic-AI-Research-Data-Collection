"""Generate PRISMA-oriented report artefacts and evaluation summary."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def reconcile_prisma(
    prisma_part1: dict,
    screened: list[dict],
    extractions: list[dict],
) -> dict[str, Any]:
    decisions = [r.get("fulltext_decision") for r in screened]
    included = decisions.count("include")
    excluded_ft = decisions.count("exclude")
    uncertain = decisions.count("uncertain")
    return {
        **(prisma_part1 or {}),
        "fulltext_assessed": len(screened),
        "fulltext_excluded": excluded_ft,
        "fulltext_uncertain": uncertain,
        "records_included": included,
        "studies_in_evidence_table": len(extractions),
        "reconciled_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Part 2 reconciles preliminary Part 1 counts with full-text / human decisions. "
            "Do not report automated preliminary title/abstract excludes as final PRISMA excludes "
            "unless confirmed by human review."
        ),
    }


def build_evaluation(
    screened: list[dict],
    extractions: list[dict],
    rob: list[dict],
    critic: dict,
    synthesis: dict,
    rag_meta: dict,
) -> dict[str, Any]:
    included = [r for r in screened if r.get("fulltext_decision") == "include"]
    with_rationale = sum(1 for r in screened if r.get("fulltext_reason"))
    human_final = sum(1 for r in screened if r.get("fulltext_is_final"))
    return {
        "completeness": {
            "screened": len(screened),
            "included": len(included),
            "extracted": len(extractions),
            "appraised": len(rob),
            "extraction_coverage": round(len(extractions) / max(len(included), 1), 3),
        },
        "transparency": {
            "decisions_with_rationale": with_rationale,
            "rationale_rate": round(with_rationale / max(len(screened), 1), 3),
            "human_final_decisions": human_final,
            "critic_verdict": critic.get("verdict"),
            "critic_score": critic.get("quality_score"),
        },
        "consistency": {
            "critic_issues": critic.get("issues", []),
            "inter_agent_checks": critic.get("checks", {}),
        },
        "rag": rag_meta,
        "synthesis_method": synthesis.get("synthesis_method"),
        "time_savings_note": (
            "Part 2 automates full-text triage drafting, extraction tables, RoB checklists, "
            "RAG-grounded narrative synthesis and QA critique. Measured wall-clock savings "
            "depend on corpus size; compare against manual screening/extraction logs for the demo topic."
        ),
    }


def render_manuscript(
    protocol: dict,
    prisma: dict,
    synthesis: dict,
    critic: dict,
    extractions: list[dict],
) -> str:
    topic = protocol.get("topic", "Untitled topic")
    lines = [
        f"# Systematic Review Draft: {topic}",
        "",
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_",
        "",
        "## Research question",
        protocol.get("research_question", ""),
        "",
        "## Methods (summary)",
        f"- Guideline: {protocol.get('guideline', 'PRISMA 2020')}",
        f"- Sources (Part 1): {', '.join(protocol.get('sources') or ['OpenAlex'])}",
        f"- Inclusion criteria: {protocol.get('inclusion_criteria') or 'see protocol file'}",
        f"- Exclusion criteria: {protocol.get('exclusion_criteria') or 'see protocol file'}",
        "",
        "## PRISMA flow (reconciled)",
        f"- Records identified (Part 1): {prisma.get('records_identified', 'n/a')}",
        f"- Duplicates removed: {prisma.get('duplicates_removed', 'n/a')}",
        f"- Title/abstract screened (Part 1): {prisma.get('records_screened_title_abstract', 'n/a')}",
        f"- Full-text assessed (Part 2): {prisma.get('fulltext_assessed', 'n/a')}",
        f"- Full-text excluded: {prisma.get('fulltext_excluded', 'n/a')}",
        f"- Studies included: {prisma.get('records_included', 'n/a')}",
        "",
        synthesis.get("narrative_markdown") or "## Narrative synthesis\n_No synthesis available._",
        "",
        "## Evidence table (compact)",
    ]
    if not extractions:
        lines.append("_No extractions._")
    else:
        for row in extractions:
            lines.append(
                f"- **{row.get('title', 'Untitled')}** ({row.get('year', 'n.d.')}) — "
                f"design: {row.get('study_design')}; findings: {(row.get('key_findings') or '')[:180]}"
            )
    lines.extend([
        "",
        "## Quality assurance",
        f"- Critic verdict: **{critic.get('verdict')}** (score {critic.get('quality_score')})",
        f"- Method: {critic.get('critic_method')}",
        f"- Recommendation: {critic.get('recommendation')}",
        "",
    ])
    return "\n".join(lines)


def export_part2_artefacts(
    output_dir: str | Path,
    protocol: dict,
    screened: list[dict],
    extractions: list[dict],
    rob: list[dict],
    synthesis: dict,
    critic: dict,
    prisma: dict,
    evaluation: dict,
) -> str:
    out = Path(output_dir)
    part2 = out / "part2"
    part2.mkdir(parents=True, exist_ok=True)

    def dump(name: str, value: Any) -> None:
        (part2 / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    dump("fulltext_screening.json", screened)
    dump("evidence_table.json", extractions)
    dump("risk_of_bias.json", rob)
    dump("synthesis.json", synthesis)
    dump("critic_report.json", critic)
    dump("prisma_reconciled.json", prisma)
    dump("evaluation.json", evaluation)

    if extractions:
        pd.DataFrame(extractions).to_csv(part2 / "evidence_table.csv", index=False, encoding="utf-8-sig")
    if rob:
        flat_rob = []
        for row in rob:
            flat = {
                "study_id": row.get("study_id"),
                "title": row.get("title"),
                "year": row.get("year"),
                "overall_risk_of_bias": row.get("overall_risk_of_bias"),
                "appraisal_method": row.get("appraisal_method"),
            }
            for domain, payload in (row.get("domains") or {}).items():
                flat[f"{domain}_judgement"] = payload.get("judgement")
                flat[f"{domain}_rationale"] = payload.get("rationale")
            flat_rob.append(flat)
        pd.DataFrame(flat_rob).to_csv(part2 / "risk_of_bias.csv", index=False, encoding="utf-8-sig")

    manuscript = render_manuscript(protocol, prisma, synthesis, critic, extractions)
    md_path = part2 / "review_manuscript_draft.md"
    md_path.write_text(manuscript, encoding="utf-8")
    try:
        from tools.report_pdf import markdown_to_pdf
        markdown_to_pdf(manuscript, part2 / "review_manuscript_draft.pdf")
    except Exception:
        # PDF export is best-effort; Markdown remains the canonical artefact.
        pass

    bib_lines = []
    for row in extractions:
        doi = row.get("doi") or ""
        title = (row.get("title") or "Untitled").replace("{", "").replace("}", "")
        year = row.get("year") or "n.d."
        key = (doi or title[:40]).replace("/", "_")
        bib_lines.append(
            f"@article{{{key},\n  title = {{{title}}},\n  year = {{{year}}},\n  doi = {{{doi}}}\n}}\n"
        )
    (part2 / "included_studies.bib").write_text("\n".join(bib_lines), encoding="utf-8")
    return str(part2.resolve())
