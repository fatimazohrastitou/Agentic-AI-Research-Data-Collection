from typing import TypedDict
from pathlib import Path
import json
import re
from langgraph.graph import StateGraph, END
from agents.protocol_agent import generate_protocol, save_protocol
from agents.search_strategy_agent import build_search_strategy, save_strategy
from agents.retrieval_agent import retrieve_literature, save_retrieved
from agents.deduplication_agent import deduplicate_articles
from agents.data_quality_agent import assess_data_quality
from agents.relevance_agent import score_relevance
from agents.screening_agent import screen_title_abstract
from tools.export_tool import export_results
from tools.pdf_acquisition import acquire_open_pdfs

class PipelineState(TypedDict, total=False):
    topic: str
    research_question: str
    inclusion_criteria: list
    exclusion_criteria: list
    include_types: list
    exclude_types: list
    year_from: int | None
    year_to: int | None
    max_results: int
    download_pdfs: bool
    protocol: dict
    strategy: dict
    retrieved: list
    unique: list
    duplicates: list
    quality_checked: list
    relevance_scored: list
    screened: list
    pdf_acquisition: list
    statistics: dict
    output_dir: str


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:70] or "research_topic"


def node_protocol(s):
    effective_exclude_types = s.get("exclude_types") or ["letter", "editorial"]
    p = generate_protocol(
        s["topic"], s.get("research_question", ""),
        s.get("inclusion_criteria"), s.get("exclusion_criteria"),
        s.get("year_from"), s.get("year_to"),
        document_types={"accepted_by_default": ["article", "review", "proceedings-article", "book-chapter"], "include_allow_list": s.get("include_types", []), "exclude": effective_exclude_types}
    )
    base = Path(s["output_dir"])
    save_protocol(p, base / "research_protocol.json")
    return {"protocol": p}

def node_strategy(s):
    x = build_search_strategy(s["topic"], s.get("research_question", ""))
    save_strategy(x, Path(s["output_dir"]) / "search_strategy.json")
    return {"strategy": x}

def node_retrieval(s):
    a = retrieve_literature(s["strategy"], s["protocol"], s.get("max_results", 100))
    save_retrieved(a, Path(s["output_dir"]) / "articles_raw.json")
    return {"retrieved": a}

def node_dedup(s):
    unique, duplicates = deduplicate_articles(s.get("retrieved", []))
    return {"unique": unique, "duplicates": duplicates}

def node_quality(s):
    return {"quality_checked": assess_data_quality(s.get("unique", []))}

def node_relevance(s):
    scored = score_relevance(
        s.get("quality_checked", []),
        s.get("topic", ""),
        s.get("research_question", ""),
        s.get("inclusion_criteria", [])
    )
    return {"relevance_scored": scored}


def node_screening(s):
    return {"screened": screen_title_abstract(
        s.get("relevance_scored", []), s.get("inclusion_criteria"),
        s.get("exclusion_criteria"), s.get("include_types"), s.get("exclude_types") or ["letter", "editorial"]
    )}

def node_pdf(s):
    if not s.get("download_pdfs"):
        return {"pdf_acquisition": []}
    # Do not spend time downloading records already excluded by the preliminary protocol.
    candidates = [x for x in s.get("screened", []) if x.get("title_abstract_decision") != "exclude"]
    return {"pdf_acquisition": acquire_open_pdfs(candidates, Path(s["output_dir"]) / "full_texts")}

def node_export(s):
    screened = s.get("screened", [])
    decisions = [x.get("title_abstract_decision") for x in screened]
    excluded = [x for x in screened if x.get("title_abstract_decision") == "exclude"]
    type_excluded = [x for x in excluded if x.get("screening_exclusion_category") == "publication_type"]
    keyword_excluded = [x for x in excluded if x.get("screening_exclusion_category") == "keyword"]
    handoff = [x for x in screened if x.get("title_abstract_decision") != "exclude"]
    stats = {
        "records_identified": len(s.get("retrieved", [])),
        "duplicates_removed": len(s.get("duplicates", [])),
        "records_after_deduplication": len(s.get("unique", [])),
        "records_screened_title_abstract": len(screened),
        "excluded_title_abstract_preliminary": len(excluded),
        "excluded_by_publication_type_preliminary": len(type_excluded),
        "excluded_by_keyword_preliminary": len(keyword_excluded),
        "potentially_include_preliminary": decisions.count("potentially_include"),
        "uncertain_preliminary": decisions.count("uncertain"),
        "needs_human_review": len(handoff),
        "relevance_scoring": {
            "method": "local_weighted_lexical_v1_no_llm",
            "high_relevance": sum(x.get("relevance_band") == "high" for x in screened),
            "medium_relevance": sum(x.get("relevance_band") == "medium" for x in screened),
            "low_relevance": sum(x.get("relevance_band") == "low" for x in screened),
            "note": "Weighted lexical term coverage with title emphasis and phrase bonus. Scores are ranking aids, not semantic judgments or final inclusion/exclusion decisions. Human screening remains required."
        },
        "publication_type_policy": {
            "accepted_by_default": ["article", "review", "proceedings-article (conference paper)", "book-chapter"],
            "excluded_by_default": ["letter", "editorial"],
            "note": "Other publication types are not automatically excluded unless an explicit include-types allow-list is supplied."
        },
        "pdf_downloaded": sum(x.get("status") == "downloaded" for x in s.get("pdf_acquisition", [])),
        "note": "All automated decisions are preliminary. Validate against the approved protocol and conduct human screening before reporting PRISMA totals."
    }
    out = export_results(screened, screened, s.get("duplicates", []), stats, s["output_dir"])
    (Path(out) / "part2_handoff.json").write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(out) / "potentially_include.json").write_text(json.dumps([x for x in handoff if x.get("title_abstract_decision") == "potentially_include"], ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(out) / "uncertain.json").write_text(json.dumps([x for x in handoff if x.get("title_abstract_decision") in ("uncertain", "needs_human_review")], ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(out) / "pdf_acquisition_results.json").write_text(json.dumps(s.get("pdf_acquisition", []), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"statistics": stats, "output_dir": out}

def build_pipeline():
    g = StateGraph(PipelineState)
    for name, fn in [("protocol",node_protocol),("strategy",node_strategy),("retrieval",node_retrieval),("deduplication",node_dedup),("data_quality",node_quality),("relevance_scoring",node_relevance),("screening",node_screening),("pdf_acquisition",node_pdf),("export",node_export)]:
        g.add_node(name, fn)
    g.set_entry_point("protocol")
    for a,b in [("protocol","strategy"),("strategy","retrieval"),("retrieval","deduplication"),("deduplication","data_quality"),("data_quality","relevance_scoring"),("relevance_scoring","screening"),("screening","pdf_acquisition"),("pdf_acquisition","export")]:
        g.add_edge(a,b)
    g.add_edge("export", END)
    return g.compile()

def run_pipeline(**kwargs):
    kwargs.setdefault("output_dir", str(Path("outputs") / _slug(kwargs["topic"])))
    return build_pipeline().invoke(kwargs)
