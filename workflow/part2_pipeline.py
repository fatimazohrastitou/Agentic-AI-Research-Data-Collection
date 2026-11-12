"""LangGraph Part 2 pipeline: full-text → extraction → RoB → RAG → synthesis → critic → report."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.critic_agent import critique_outputs
from agents.extraction_agent import extract_evidence
from agents.fulltext_screening_agent import screen_fulltext
from agents.report_agent import build_evaluation, export_part2_artefacts, reconcile_prisma
from agents.risk_of_bias_agent import appraise_risk_of_bias
from agents.synthesis_agent import synthesise_evidence
from tools.handoff_loader import load_part2_inputs
from tools.llm_config import llm_mode
from tools.rag_store import build_rag_index


class Part2State(TypedDict, total=False):
    output_dir: str
    protocol: dict
    prisma_part1: dict
    records: list
    screened: list
    extractions: list
    risk_of_bias: list
    rag_meta: dict
    rag_dir: str
    synthesis: dict
    critic: dict
    prisma: dict
    evaluation: dict
    part2_dir: str
    load_stats: dict


def node_load(state: Part2State) -> dict:
    payload = load_part2_inputs(state["output_dir"])
    return {
        "protocol": payload["protocol"],
        "prisma_part1": payload["prisma_part1"],
        "records": payload["records"],
        "load_stats": {
            "human_decisions_applied": payload["human_decisions_applied"],
            "records_with_full_text": payload["records_with_full_text"],
            "records_pdf_parsed": payload["records_pdf_parsed"],
            "n_records": len(payload["records"]),
            "llm_mode": llm_mode(),
        },
    }


def node_fulltext(state: Part2State) -> dict:
    screened = screen_fulltext(state.get("records", []), state.get("protocol") or {})
    return {"screened": screened}


def node_extraction(state: Part2State) -> dict:
    return {"extractions": extract_evidence(state.get("screened", []), state.get("protocol") or {})}


def node_rob(state: Part2State) -> dict:
    return {"risk_of_bias": appraise_risk_of_bias(state.get("screened", []))}


def node_rag(state: Part2State) -> dict:
    out = Path(state["output_dir"])
    rag_dir = out / "part2" / "rag_index"
    included = [r for r in state.get("screened", []) if r.get("included_for_extraction")]
    # Index included studies; if none yet, index all available texts for exploratory retrieval.
    corpus = included or state.get("screened", [])
    meta = build_rag_index(corpus, rag_dir)
    return {"rag_meta": meta, "rag_dir": str(rag_dir)}


def node_synthesis(state: Part2State) -> dict:
    synthesis = synthesise_evidence(
        state.get("protocol") or {},
        state.get("extractions") or [],
        state.get("risk_of_bias") or [],
        state.get("rag_dir") or "",
    )
    return {"synthesis": synthesis}


def node_critic(state: Part2State) -> dict:
    prisma = reconcile_prisma(
        state.get("prisma_part1") or {},
        state.get("screened") or [],
        state.get("extractions") or [],
    )
    critic = critique_outputs(
        state.get("protocol") or {},
        state.get("screened") or [],
        state.get("extractions") or [],
        state.get("risk_of_bias") or [],
        state.get("synthesis") or {},
        prisma,
    )
    return {"prisma": prisma, "critic": critic}


def node_export(state: Part2State) -> dict:
    evaluation = build_evaluation(
        state.get("screened") or [],
        state.get("extractions") or [],
        state.get("risk_of_bias") or [],
        state.get("critic") or {},
        state.get("synthesis") or {},
        state.get("rag_meta") or {},
    )
    part2_dir = export_part2_artefacts(
        state["output_dir"],
        state.get("protocol") or {},
        state.get("screened") or [],
        state.get("extractions") or [],
        state.get("risk_of_bias") or [],
        state.get("synthesis") or {},
        state.get("critic") or {},
        state.get("prisma") or {},
        evaluation,
    )
    return {"evaluation": evaluation, "part2_dir": part2_dir}


def build_part2_pipeline():
    g = StateGraph(Part2State)
    nodes = [
        ("load_inputs", node_load),
        ("fulltext_screening", node_fulltext),
        ("extraction", node_extraction),
        ("risk_of_bias", node_rob),
        ("rag_index", node_rag),
        ("synthesis", node_synthesis),
        ("critic", node_critic),
        ("export", node_export),
    ]
    for name, fn in nodes:
        g.add_node(name, fn)
    g.set_entry_point("load_inputs")
    edges = [
        ("load_inputs", "fulltext_screening"),
        ("fulltext_screening", "extraction"),
        ("extraction", "risk_of_bias"),
        ("risk_of_bias", "rag_index"),
        ("rag_index", "synthesis"),
        ("synthesis", "critic"),
        ("critic", "export"),
    ]
    for a, b in edges:
        g.add_edge(a, b)
    g.add_edge("export", END)
    return g.compile()


def run_part2_pipeline(output_dir: str) -> dict:
    app = build_part2_pipeline()
    return app.invoke({"output_dir": str(Path(output_dir))})
