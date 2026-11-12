"""
RevuAgent — Streamlit interface for the agentic systematic review pipeline.

Run from project root:
  python -m streamlit run ui/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.charts import (  # noqa: E402
    animated_year_decisions,
    band_bars,
    decision_donut,
    prisma_funnel_chart,
    relevance_scatter,
)
from ui.viz import (  # noqa: E402
    OUTPUTS,
    as_dataframe,
    list_output_runs,
    load_run_bundle,
    prisma_funnel_rows,
    run_dir,
    screening_summary,
)

ICON_PATH = Path(__file__).resolve().parent / "assets" / "revuagent_icon.png"

st.set_page_config(
    page_title="RevuAgent",
    page_icon=str(ICON_PATH) if ICON_PATH.is_file() else ":books:",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

:root {
  --ink: #0c1220;
  --panel: rgba(255,255,255,0.72);
  --accent: #067a63;
  --accent-2: #1aa6a0;
  --warm: #e4572e;
  --amber: #f0a202;
  --deep: #12355b;
  --line: rgba(18,53,91,0.12);
  --muted: #5a6777;
  --glass: blur(14px);
}

@keyframes aurora {
  0% { background-position: 0% 40%, 100% 0%, 50% 100%; }
  50% { background-position: 40% 60%, 60% 30%, 20% 80%; }
  100% { background-position: 0% 40%, 100% 0%, 50% 100%; }
}
@keyframes riseIn {
  from { opacity: 0; transform: translateY(22px) scale(0.97); filter: blur(4px); }
  to { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}
@keyframes floatSoft {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(4deg); }
}
@keyframes spinSlow {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes dash {
  to { stroke-dashoffset: 0; }
}
@keyframes barGrow {
  from { transform: scaleX(0); }
  to { transform: scaleX(1); }
}
@keyframes pulseRing {
  0% { box-shadow: 0 0 0 0 rgba(26,166,160,0.35); }
  70% { box-shadow: 0 0 0 16px rgba(26,166,160,0); }
  100% { box-shadow: 0 0 0 0 rgba(26,166,160,0); }
}
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-18px); }
  to { opacity: 1; transform: translateX(0); }
}

html, body, [class*="css"] {
  font-family: Manrope, sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(900px 500px at 8% 12%, rgba(26,166,160,0.35), transparent 60%),
    radial-gradient(800px 480px at 92% 8%, rgba(228,87,46,0.22), transparent 55%),
    radial-gradient(700px 520px at 70% 90%, rgba(240,162,2,0.18), transparent 50%),
    linear-gradient(145deg, #f4f7f5 0%, #eef3f7 45%, #f7f1ea 100%);
  background-size: 140% 140%, 140% 140%, 140% 140%, 100% 100%;
  animation: aurora 16s ease-in-out infinite;
}

/* Hide default Streamlit chrome clutter a bit */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

h1, h2, h3, .brand-title {
  font-family: Syne, sans-serif !important;
  letter-spacing: -0.03em;
}

.hero {
  position: relative;
  overflow: hidden;
  border-radius: 28px;
  padding: 1.2rem 1.35rem 1.3rem;
  margin-bottom: 1.15rem;
  color: #f7fbff;
  background:
    linear-gradient(120deg, rgba(12,18,32,0.94), rgba(18,53,91,0.92) 48%, rgba(6,122,99,0.82));
  box-shadow: 0 24px 50px rgba(12,18,32,0.18);
  animation: riseIn 0.65s cubic-bezier(.2,.8,.2,1) both;
  display: grid;
  grid-template-columns: 118px 1fr;
  gap: 1.1rem;
  align-items: center;
}
.hero-logo {
  width: 108px;
  height: 108px;
  border-radius: 26px;
  object-fit: cover;
  box-shadow: 0 14px 30px rgba(0,0,0,0.28);
  animation: floatSoft 4s ease-in-out infinite;
  border: 2px solid rgba(240,162,2,0.45);
  background: #0c1220;
}
.hero-copy { position: relative; z-index: 1; }
.hero::before {
  content: "";
  position: absolute;
  width: 220px; height: 220px;
  right: -40px; top: -60px;
  border-radius: 50%;
  border: 18px solid rgba(255,255,255,0.08);
  animation: spinSlow 18s linear infinite;
}
.hero::after {
  content: "";
  position: absolute;
  width: 140px; height: 140px;
  right: 70px; bottom: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(240,162,2,0.55), transparent 70%);
  animation: floatSoft 4.5s ease-in-out infinite;
}
.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.82);
  margin-bottom: 0.55rem;
}
.hero-kicker i {
  width: 8px; height: 8px; border-radius: 50%;
  background: #f0a202;
  display: inline-block;
  animation: pulseRing 2s infinite;
}
.brand-title {
  font-size: clamp(1.85rem, 3.4vw, 2.7rem);
  margin: 0;
  line-height: 1.05;
  color: #fff;
}
.brand-title span.gold { color: #f0d7a3; font-weight: 700; }
.brand-sub {
  margin-top: 0.55rem;
  max-width: 46rem;
  color: rgba(247,251,255,0.88);
  font-size: 1.02rem;
  line-height: 1.45;
}
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0.2rem 0 1rem 0;
  animation: riseIn 0.45s ease both;
}
.sidebar-brand img {
  width: 42px; height: 42px; border-radius: 12px;
  border: 1px solid rgba(240,162,2,0.35);
}
.sidebar-brand strong {
  font-family: Syne, sans-serif;
  font-size: 1.05rem;
  letter-spacing: -0.02em;
}

.flow {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 1rem 0 1.35rem 0;
}
.flow-step {
  position: relative;
  background: var(--panel);
  backdrop-filter: var(--glass);
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 0.95rem 0.85rem;
  min-height: 118px;
  box-shadow: 0 12px 30px rgba(12,18,32,0.06);
  animation: riseIn 0.55s cubic-bezier(.2,.8,.2,1) both;
  transition: transform 0.28s ease, box-shadow 0.28s ease;
  overflow: hidden;
}
.flow-step::before {
  content: "";
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: linear-gradient(180deg, var(--deep), var(--accent-2));
}
.flow-step:nth-child(1) { animation-delay: 0.04s; }
.flow-step:nth-child(2) { animation-delay: 0.10s; }
.flow-step:nth-child(3) { animation-delay: 0.16s; }
.flow-step:nth-child(4) { animation-delay: 0.22s; }
.flow-step:nth-child(5) { animation-delay: 0.28s; }
.flow-step:nth-child(6) { animation-delay: 0.34s; }
.flow-step:hover {
  transform: translateY(-6px) scale(1.01);
  box-shadow: 0 18px 36px rgba(12,18,32,0.12);
}
.flow-step .n {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
.flow-step .t {
  display: block;
  margin-top: 0.4rem;
  font-family: Syne, sans-serif;
  font-weight: 700;
  font-size: 1rem;
}
.flow-step .d {
  display: block;
  margin-top: 0.28rem;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.35;
}
.flow-step.done {
  background: linear-gradient(160deg, rgba(6,122,99,0.12), rgba(255,255,255,0.85));
  border-color: rgba(6,122,99,0.35);
}
.flow-step.wait {
  background: linear-gradient(160deg, rgba(228,87,46,0.10), rgba(255,255,255,0.85));
  border-color: rgba(228,87,46,0.28);
}

.metric-card {
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 1.05rem 1.1rem 1.2rem;
  box-shadow: 0 14px 34px rgba(12,18,32,0.07);
  animation: riseIn 0.55s cubic-bezier(.2,.8,.2,1) both;
}
.metric-card::before {
  content: "";
  position: absolute;
  width: 120px; height: 120px;
  right: -35px; top: -45px;
  border-radius: 50%;
  opacity: 0.35;
}
.metric-card.tone-green::before { background: radial-gradient(circle, #1aa6a0, transparent 70%); }
.metric-card.tone-amber::before { background: radial-gradient(circle, #f0a202, transparent 70%); }
.metric-card.tone-red::before { background: radial-gradient(circle, #e4572e, transparent 70%); }
.metric-card.tone-blue::before { background: radial-gradient(circle, #12355b, transparent 70%); }
.metric-card::after {
  content: "";
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 5px;
  transform-origin: left;
  animation: barGrow 0.85s cubic-bezier(.2,.8,.2,1) both;
}
.metric-card.tone-green::after { background: linear-gradient(90deg, #067a63, #1aa6a0); }
.metric-card.tone-amber::after { background: linear-gradient(90deg, #f0a202, #ffd166); }
.metric-card.tone-red::after { background: linear-gradient(90deg, #e4572e, #ff7a59); }
.metric-card.tone-blue::after { background: linear-gradient(90deg, #12355b, #3a7ca5); }
.metric-card .label {
  position: relative;
  z-index: 1;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.metric-card .value {
  position: relative;
  z-index: 1;
  font-family: Syne, sans-serif;
  font-size: 2rem;
  margin-top: 0.25rem;
  color: var(--ink);
}
.metric-card .hint {
  position: relative;
  z-index: 1;
  color: var(--muted);
  font-size: 0.8rem;
  margin-top: 0.2rem;
}

.status-pill {
  display: inline-block;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  margin: 0.15rem 0.28rem 0.15rem 0;
  animation: slideInLeft 0.4s ease both;
}
.ok { background: rgba(6,122,99,0.14); color: #067a63; }
.missing { background: rgba(228,87,46,0.14); color: #c2410c; }

.decision-badge {
  display: inline-block;
  padding: 0.22rem 0.6rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}
.decision-badge.include, .decision-badge.potentially_include {
  background: rgba(6,122,99,0.14); color: #067a63;
}
.decision-badge.uncertain, .decision-badge.needs_human_review {
  background: rgba(240,162,2,0.18); color: #9a6700;
}
.decision-badge.exclude {
  background: rgba(228,87,46,0.16); color: #c2410c;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 0.95rem;
  margin: 0.55rem 0 1rem 0;
  animation: riseIn 0.5s ease both;
}
.floating-orb {
  width: 58px; height: 58px; border-radius: 18px;
  background:
    conic-gradient(from 120deg, #12355b, #067a63, #f0a202, #e4572e, #12355b);
  animation: floatSoft 3.8s ease-in-out infinite, spinSlow 12s linear infinite;
  box-shadow: 0 14px 30px rgba(18,53,91,0.25);
  position: relative;
}
.floating-orb::after {
  content: "";
  position: absolute;
  inset: 4px;
  border-radius: 14px;
  background: rgba(255,255,255,0.85);
}
.section-head h3 {
  margin: 0;
  font-size: 1.45rem;
}
.section-head p {
  margin: 0.2rem 0 0;
  color: var(--muted);
}

.article-card {
  position: relative;
  background: linear-gradient(145deg, rgba(255,255,255,0.92), rgba(244,247,245,0.88));
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 1rem 1.05rem;
  margin: 0.65rem 0;
  animation: riseIn 0.45s ease both;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  overflow: hidden;
}
.article-card::before {
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6px;
  background: linear-gradient(180deg, #067a63, #f0a202, #e4572e);
}
.article-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 18px 36px rgba(12,18,32,0.12);
}
.article-card .meta { color: var(--muted); font-size: 0.85rem; margin-top: 0.35rem; }
.score-bar {
  margin-top: 0.65rem;
  height: 9px;
  background: rgba(18,53,91,0.08);
  border-radius: 99px;
  overflow: hidden;
}
.score-bar > span {
  display: block;
  height: 100%;
  border-radius: 99px;
  transform-origin: left;
  animation: barGrow 1s cubic-bezier(.2,.8,.2,1) both;
  background: linear-gradient(90deg, #12355b, #067a63, #f0a202, #e4572e);
  background-size: 200% 100%;
  animation: barGrow 1s cubic-bezier(.2,.8,.2,1) both, aurora 4s linear infinite;
}

.callout {
  background: linear-gradient(120deg, #12355b, #067a63 55%, #e4572e);
  background-size: 200% 200%;
  animation: aurora 8s ease infinite, riseIn 0.5s ease both;
  color: #f7fbff;
  border-radius: 22px;
  padding: 1.15rem 1.3rem;
  margin: 0.6rem 0 1.1rem 0;
  box-shadow: 0 16px 40px rgba(18,53,91,0.2);
}
.callout strong { color: #fff; }
.callout p { margin: 0.35rem 0 0 0; opacity: 0.92; }

.report-box {
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(10px);
  border: 1px solid var(--line);
  border-radius: 22px;
  padding: 1.1rem 1.2rem;
  animation: riseIn 0.5s ease both;
  box-shadow: 0 14px 34px rgba(12,18,32,0.06);
}

/* Streamlit controls */
div[data-testid="stSidebar"] {
  background:
    linear-gradient(175deg, #0c1220 0%, #12355b 48%, #067a63 130%);
  border-right: 1px solid rgba(255,255,255,0.06);
}
div[data-testid="stSidebar"] * { color: #eef3f6 !important; }
div[data-testid="stSidebar"] .stRadio label {
  color: #d5dee6 !important;
  padding: 0.35rem 0.2rem;
  border-radius: 10px;
  transition: background 0.2s ease;
}
div[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255,255,255,0.06);
}
div.stButton > button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: linear-gradient(120deg, #067a63, #1aa6a0 45%, #e4572e) !important;
  background-size: 180% 180% !important;
  border: none !important;
  color: white !important;
  font-weight: 700 !important;
  border-radius: 14px !important;
  box-shadow: 0 12px 28px rgba(6,122,99,0.28) !important;
  animation: aurora 6s ease infinite;
  transition: transform 0.2s ease, box-shadow 0.2s ease !important;
}
div.stButton > button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: 0 16px 34px rgba(228,87,46,0.28) !important;
}
div[data-testid="stForm"] {
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(10px);
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 0.6rem 0.85rem 1rem;
  box-shadow: 0 16px 40px rgba(12,18,32,0.06);
  animation: riseIn 0.5s ease both;
}

@media (max-width: 1100px) {
  .flow { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .flow { grid-template-columns: 1fr 1fr; }
  .hero { grid-template-columns: 1fr; text-align: left; }
  .hero-logo { width: 88px; height: 88px; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _icon_data_uri() -> str:
    import base64
    if not ICON_PATH.is_file():
        return ""
    b64 = base64.b64encode(ICON_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def header(subtitle: str | None = None):
    logo = _icon_data_uri()
    logo_html = f'<img class="hero-logo" src="{logo}" alt="RevuAgent" />' if logo else ""
    st.markdown(
        f"""
        <div class="hero">
          {logo_html}
          <div class="hero-copy">
            <div class="hero-kicker"><i></i> Agentic PRISMA Pipeline</div>
            <div class="brand-title">Revu<span class="gold">Agent</span></div>
            <div class="brand-sub">{subtitle or "Collecte, screening, extraction, RAG et rapport — un pipeline vivant pour la revue systématique."}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: object, hint: str = "", tone: str = "blue"):
    st.markdown(
        f"""
        <div class="metric-card tone-{tone}">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def select_run(label: str = "Run outputs/") -> str | None:
    runs = list_output_runs()
    if not runs:
        return None
    default = st.session_state.get("selected_run")
    idx = runs.index(default) if default in runs else 0
    selected = st.selectbox(label, runs, index=idx)
    st.session_state["selected_run"] = selected
    return selected


def show_flow(bundle: dict | None = None):
    s1 = (bundle or {}).get("status1") or {}
    s2 = (bundle or {}).get("status2") or {}

    def cls(ok: bool | None) -> str:
        if ok is True:
            return "done"
        if ok is False:
            return "wait"
        return ""

    steps = [
        ("01", "Protocole", "Draft PRISMA + critères", s1.get("protocol")),
        ("02", "Retrieval", "OpenAlex + stratégie", s1.get("articles") or s1.get("strategy")),
        ("03", "Screening P1", "Titre / résumé préliminaire", s1.get("screening")),
        ("04", "Handoff", "Excel humain + JSON", s1.get("handoff")),
        ("05", "Analyse P2", "Full-text, extraction, RoB, RAG", s2.get("evidence") or s2.get("fulltext")),
        ("06", "Rapport", "Manuscrit + PRISMA + critic", s2.get("manuscript")),
    ]
    cards = []
    for n, title, desc, ok in steps:
        cards.append(
            f'<div class="flow-step {cls(ok)}"><div class="n">Étape {n}</div>'
            f'<span class="t">{title}</span><span class="d">{desc}</span></div>'
        )
    st.markdown(f'<div class="flow">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_funnel(prisma: dict):
    df = prisma_funnel_rows(prisma or {})
    if df.empty:
        st.caption("Pas encore de compteurs PRISMA pour ce run.")
        return
    st.markdown("#### Entonnoir PRISMA")
    st.plotly_chart(prisma_funnel_chart(prisma or {}), width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)


def _download_buttons(folder: Path, files: list[tuple[str, Path, str]], key_prefix: str):
    cols = st.columns(3)
    for i, (label, path, mime) in enumerate(files):
        with cols[i % 3]:
            if path.is_file():
                st.download_button(
                    label=f"Télécharger — {label}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime=mime,
                    key=f"{key_prefix}-{folder.name}-{path.name}",
                    use_container_width=True,
                )
            else:
                st.button(
                    f"{label} (absent)",
                    disabled=True,
                    use_container_width=True,
                    key=f"{key_prefix}-miss-{folder.name}-{path.name}",
                )


def ensure_report_pdf(folder: Path) -> Path | None:
    """Create the manuscript PDF on demand if missing."""
    md = folder / "part2" / "review_manuscript_draft.md"
    pdf = folder / "part2" / "review_manuscript_draft.pdf"
    if pdf.is_file():
        return pdf
    if not md.is_file():
        return None
    try:
        from tools.report_pdf import write_manuscript_pdf
        return write_manuscript_pdf(md, pdf)
    except Exception:
        return None


def render_downloads(folder: Path):
    ensure_report_pdf(folder)
    files = [
        ("Rapport PDF", folder / "part2" / "review_manuscript_draft.pdf", "application/pdf"),
        ("Manuscrit Markdown", folder / "part2" / "review_manuscript_draft.md", "text/markdown"),
        ("Evidence CSV", folder / "part2" / "evidence_table.csv", "text/csv"),
        ("Human review Excel", folder / "human_review.xlsx",
         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]
    _download_buttons(folder, files, "p2")


def _authors_str(authors) -> str:
    if not authors:
        return ""
    names = []
    for a in authors:
        if isinstance(a, dict):
            names.append(str(a.get("display_name") or a.get("name") or ""))
        else:
            names.append(str(a))
    return "; ".join(n for n in names if n)


def screening_table(records: list[dict]) -> pd.DataFrame:
    rows = []
    for i, item in enumerate(records or [], start=1):
        rows.append({
            "#": i,
            "title": item.get("title") or "",
            "year": item.get("year") or "",
            "type": item.get("type") or "",
            "decision": item.get("title_abstract_decision") or "",
            "relevance": item.get("relevance_band") or "",
            "score": item.get("relevance_score"),
            "reason": item.get("title_abstract_reason") or "",
            "authors": _authors_str(item.get("authors")),
            "venue": item.get("venue") or "",
            "doi": item.get("doi") or "",
            "is_oa": item.get("is_oa"),
            "pdf_url": item.get("pdf_url") or item.get("oa_url") or "",
            "abstract": (item.get("abstract") or "")[:400],
        })
    df = pd.DataFrame(rows)
    if not df.empty and "score" in df.columns:
        df = df.sort_values(["decision", "score"], ascending=[True, False], kind="stable")
    return df


def render_part1_results(folder: Path, stats: dict | None = None):
    """Rich visualization of Part 1 detected articles + downloads."""
    screening = []
    screening_path = folder / "screening_results.json"
    if screening_path.is_file():
        import json
        screening = json.loads(screening_path.read_text(encoding="utf-8"))
    elif (folder / "part2_handoff.json").is_file():
        import json
        screening = json.loads((folder / "part2_handoff.json").read_text(encoding="utf-8"))

    prisma = stats or {}
    if not prisma and (folder / "prisma_statistics.json").is_file():
        import json
        prisma = json.loads((folder / "prisma_statistics.json").read_text(encoding="utf-8"))

    if not screening and not prisma:
        st.info("Aucun article détecté pour ce dossier. Lancez Partie 1 ci-dessus.")
        return

    decisions = screening_summary(screening, "title_abstract_decision")
    bands = screening_summary(screening, "relevance_band")

    st.markdown(
        """
        <div class="section-head">
          <div class="floating-orb"></div>
          <div>
            <h3>Articles détectés</h3>
            <p>Visualisation vivante du screening — couleurs = décisions & pertinence</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        metric_card("Identifiés", prisma.get("records_identified", len(screening)), "OpenAlex", tone="blue")
    with m2:
        metric_card("Après dédup", prisma.get("records_after_deduplication", len(screening)), tone="blue")
    with m3:
        metric_card(
            "Potentially include",
            decisions.get("potentially_include", prisma.get("potentially_include_preliminary", 0)),
            tone="green",
        )
    with m4:
        metric_card(
            "Uncertain",
            decisions.get("uncertain", prisma.get("uncertain_preliminary", 0)),
            tone="amber",
        )
    with m5:
        metric_card(
            "Exclus (prélim.)",
            decisions.get("exclude", prisma.get("excluded_title_abstract_preliminary", 0)),
            tone="red",
        )

    c1, c2 = st.columns(2)
    with c1:
        if decisions:
            st.plotly_chart(decision_donut(decisions, "Décisions de screening"), width="stretch")
        else:
            st.caption("Pas de décisions.")
    with c2:
        if bands:
            st.plotly_chart(band_bars(bands, "Bandes de pertinence"), width="stretch")
        else:
            st.caption("Pas de scores de pertinence.")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(relevance_scatter(screening, "Score vs année"), width="stretch")
    with c4:
        st.plotly_chart(animated_year_decisions(screening, "Articles par année / décision"), width="stretch")

    if prisma:
        with st.expander("Entonnoir PRISMA animé", expanded=True):
            render_funnel(prisma)

    df = screening_table(screening)
    if df.empty:
        st.warning("Fichier screening vide.")
        return

    st.markdown("#### Filtrer les articles")
    f1, f2, f3 = st.columns(3)
    with f1:
        decision_opts = ["(tous)"] + sorted(df["decision"].dropna().astype(str).unique().tolist())
        decision_filter = st.selectbox("Décision", decision_opts, key=f"p1-dec-{folder.name}")
    with f2:
        band_opts = ["(tous)"] + sorted(df["relevance"].dropna().astype(str).unique().tolist())
        band_filter = st.selectbox("Pertinence", band_opts, key=f"p1-band-{folder.name}")
    with f3:
        query = st.text_input("Recherche titre / DOI", "", key=f"p1-q-{folder.name}")

    view = df.copy()
    if decision_filter != "(tous)":
        view = view[view["decision"].astype(str) == decision_filter]
    if band_filter != "(tous)":
        view = view[view["relevance"].astype(str) == band_filter]
    if query.strip():
        q = query.strip().lower()
        view = view[
            view["title"].astype(str).str.lower().str.contains(q, na=False)
            | view["doi"].astype(str).str.lower().str.contains(q, na=False)
        ]

    st.caption(f"{len(view)} / {len(df)} article(s) affiché(s)")
    st.dataframe(
        view[["#", "title", "year", "type", "decision", "relevance", "score", "reason", "authors", "venue", "doi", "is_oa"]],
        width="stretch",
        hide_index=True,
        height=420,
    )

    st.markdown("#### Cartes articles (aperçu coloré)")
    for idx, (_, row) in enumerate(view.head(24).iterrows()):
        badge = str(row.get("decision") or "unknown")
        title = str(row.get("title") or "Sans titre")
        score = row.get("score")
        try:
            score_pct = max(0, min(100, int(float(score) * 100))) if score is not None and str(score) != "" else 0
        except Exception:
            score_pct = 0
        delay = min(idx * 0.04, 0.6)
        st.markdown(
            f"""
            <div class="article-card" style="animation-delay:{delay}s">
              <span class="decision-badge {badge}">{badge}</span>
              <span class="decision-badge" style="background:#e8eef5;color:#16324f;margin-left:0.35rem">{row.get('relevance') or 'n/a'}</span>
              <div style="font-weight:700;margin-top:0.45rem;font-size:1.02rem">{title}</div>
              <div class="meta">{row.get('year') or 'n.d.'} · {row.get('type') or '—'} · {row.get('venue') or '—'}</div>
              <div class="meta" style="margin-top:0.25rem">{(row.get('reason') or '')[:180]}</div>
              <div class="score-bar" title="relevance score"><span style="width:{score_pct}%"></span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"Détails — {title[:90]}"):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"**Auteurs :** {row.get('authors') or '—'}")
                st.markdown(f"**Raison screening :** {row.get('reason') or '—'}")
                st.markdown(f"**Abstract (extrait) :** {row.get('abstract') or '_non disponible_'}")
            with c2:
                st.markdown(f"**Score :** `{row.get('score')}`")
                st.markdown(f"**DOI :** {row.get('doi') or '—'}")
                st.markdown(f"**Open access :** {row.get('is_oa')}")
                pdf = row.get("pdf_url") or ""
                if pdf:
                    st.markdown(f"[Lien PDF / OA]({pdf})")

def render_part2_launch_button(folder: Path):
    """Primary button placed right after Part 1 run (before article visuals)."""
    if st.button(
        "Générer le rapport",
        type="primary",
        use_container_width=True,
        key=f"launch-part2-{folder.name}",
    ):
        with st.spinner("en cours — screening, extraction, RAG, rapport…"):
            from workflow.part2_pipeline import run_part2_pipeline
            result = run_part2_pipeline(str(folder))
        st.session_state["selected_run"] = folder.name
        st.session_state["part2_just_ran"] = True
        st.session_state["part2_result_preview"] = {
            "prisma": result.get("prisma") or {},
            "critic": result.get("critic") or {},
            "n_extractions": len(result.get("extractions") or []),
            "llm_mode": (result.get("load_stats") or {}).get("llm_mode", "—"),
            "part2_dir": result.get("part2_dir") or "",
        }

    preview = st.session_state.get("part2_result_preview")
    if preview and st.session_state.get("selected_run") == folder.name:
        prisma = preview.get("prisma") or {}
        critic = preview.get("critic") or {}
        a, b, c, d = st.columns(4)
        with a:
            metric_card("Inclus", prisma.get("records_included", "—"), "études retenues", tone="green")
        with b:
            metric_card("Extractions", preview.get("n_extractions", 0), "evidence table", tone="blue")
        with c:
            metric_card("Critic", critic.get("verdict", "—"), f"score {critic.get('quality_score', '—')}", tone="amber")
        with d:
            metric_card("LLM", preview.get("llm_mode", "—"), "mode utilisé", tone="blue")
        manuscript = Path(preview.get("part2_dir") or "") / "review_manuscript_draft.md"
        if not manuscript.is_file():
            manuscript = folder / "part2" / "review_manuscript_draft.md"
        if manuscript.is_file():
            with st.expander("Aperçu du rapport généré", expanded=True):
                st.markdown(manuscript.read_text(encoding="utf-8"))
            render_downloads(folder)


def page_run_part1():
    header("Partie 1 — lancez la recherche : les articles s’affichent directement, puis générez le rapport.")
    with st.form("part1_form"):
        topic = st.text_input("Topic", value="Cybersecurity in IoT")
        question = st.text_area(
            "Research question",
            value="What security threats and mitigation techniques are studied for IoT systems?",
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            max_results = st.number_input("Max results", min_value=5, max_value=200, value=20, step=5)
        with c2:
            include = st.text_input("Inclusion terms", value="iot security threat mitigation")
        with c3:
            exclude = st.text_input("Exclusion terms", value="editorial")
        download_pdfs = st.checkbox("Télécharger PDFs open-access", value=False)
        submitted = st.form_submit_button("Exécuter Partie 1", type="primary")

    if submitted:
        if not topic.strip():
            st.error("Le topic est obligatoire.")
            return
        with st.spinner("Loading…"):
            from workflow.research_pipeline import run_pipeline
            result = run_pipeline(
                topic=topic.strip(),
                research_question=question.strip(),
                max_results=int(max_results),
                inclusion_criteria=[t for t in include.split() if t],
                exclusion_criteria=[t for t in exclude.split() if t],
                download_pdfs=download_pdfs,
            )
        name = Path(result["output_dir"]).name
        st.session_state["selected_run"] = name
        st.session_state["part1_result_stats"] = result.get("statistics") or {}
        st.session_state["part1_ready"] = True
        st.session_state.pop("part2_result_preview", None)

    # Keep results visible after reruns (needed for the Part 2 button).
    if st.session_state.get("part1_ready") and st.session_state.get("selected_run"):
        folder = run_dir(st.session_state["selected_run"])
        if (folder / "screening_results.json").is_file() or (folder / "part2_handoff.json").is_file():
            # Button replaces the old "Partie 1 terminée → outputs/..." message.
            render_part2_launch_button(folder)
            render_part1_results(folder, stats=st.session_state.get("part1_result_stats") or {})
            return

    st.caption("Remplissez le formulaire puis cliquez sur **Exécuter Partie 1** pour voir les articles détectés.")


def page_run_part2():
    header("Partie 2 — full-text, extraction, RAG, critic et génération du manuscrit.")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Créer / rafraîchir fixture démo", use_container_width=True):
            from tools.create_part2_demo_fixture import create_fixture
            path = create_fixture(OUTPUTS / "demo_cybersecurity_in_iot")
            st.session_state["selected_run"] = path.name
            st.success(f"Fixture prête : {path.name}")
            st.rerun()
    with c2:
        selected = select_run("Dossier à analyser")
        run_btn = st.button("Exécuter Partie 2 et générer le rapport", type="primary", disabled=selected is None, use_container_width=True)

    if selected is None:
        st.warning("Aucun run disponible. Lancez la Partie 1 ou créez la démo.")
        return

    folder = run_dir(selected)
    show_flow(load_run_bundle(folder))

    if run_btn:
        with st.spinner("en cours — screening, extraction, RAG, rapport…"):
            from workflow.part2_pipeline import run_part2_pipeline
            result = run_part2_pipeline(str(folder))
        st.session_state["selected_run"] = selected
        st.session_state["just_finished_part2"] = True
        prisma = result.get("prisma") or {}
        critic = result.get("critic") or {}
        st.success("Rapport généré.")
        a, b, c, d = st.columns(4)
        with a:
            metric_card("Inclus", prisma.get("records_included", "—"), "études retenues")
        with b:
            metric_card("Extractions", len(result.get("extractions") or []), "evidence table")
        with c:
            metric_card("Critic", critic.get("verdict", "—"), f"score {critic.get('quality_score', '—')}")
        with d:
            metric_card("LLM", (result.get("load_stats") or {}).get("llm_mode", "—"), "mode utilisé")

        manuscript = Path(result.get("part2_dir", "")) / "review_manuscript_draft.md"
        if manuscript.is_file():
            st.markdown("### Rapport généré (aperçu)")
            st.markdown('<div class="report-box">', unsafe_allow_html=True)
            st.markdown(manuscript.read_text(encoding="utf-8"))
            st.markdown("</div>", unsafe_allow_html=True)
            render_downloads(folder)


def page_report():
    header("Rapport final — le livrable de la Partie 2, avec téléchargements.")
    selected = select_run()
    if not selected:
        st.info("Aucun run. Créez la démo ou lancez les pipelines.")
        return

    folder = run_dir(selected)
    bundle = load_run_bundle(folder)
    show_flow(bundle)

    if not bundle.get("manuscript"):
        st.markdown(
            """
            <div class="callout">
              <strong>Aucun manuscrit pour ce run</strong>
              <p>Le fichier <code>part2/review_manuscript_draft.md</code> n’existe pas encore.
              Allez dans <b>Lancer Partie 2</b> puis cliquez sur <b>Exécuter Partie 2 et générer le rapport</b>.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    prisma = bundle.get("prisma2") or {}
    critic = bundle.get("critic") or {}
    a, b, c, d = st.columns(4)
    with a:
        metric_card("Inclus", prisma.get("records_included", "—"))
    with b:
        metric_card("Full-text", prisma.get("fulltext_assessed", "—"))
    with c:
        metric_card("Critic", critic.get("verdict", "—"))
    with d:
        metric_card("Complétion", f"{bundle.get('completion', 0)}%")

    pdf_path = ensure_report_pdf(folder)
    if pdf_path and pdf_path.is_file():
        st.download_button(
            "Télécharger le rapport PDF",
            data=pdf_path.read_bytes(),
            file_name="review_manuscript_draft.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key=f"main-pdf-{folder.name}",
        )
    else:
        st.warning("PDF indisponible pour ce run. Régénérez le rapport.")

    st.markdown("### Autres téléchargements")
    render_downloads(folder)

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("### Manuscrit draft")
        st.markdown('<div class="report-box">', unsafe_allow_html=True)
        st.markdown(bundle["manuscript"])
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        render_funnel(prisma)
        if bundle.get("evidence"):
            st.markdown("#### Evidence (aperçu)")
            st.dataframe(
                as_dataframe(bundle["evidence"], ["title", "year", "key_findings"]),
                width="stretch",
                hide_index=True,
                height=320,
            )
        path_hint = folder / "part2" / "review_manuscript_draft.md"
        st.caption(f"Fichier disque : `{path_hint}`")


def main():
    pages = [
        "Lancer Partie 1",
        "Lancer Partie 2",
        "Rapport final",
    ]
    if st.session_state.get("nav_page") not in pages:
        st.session_state["nav_page"] = "Lancer Partie 1"

    with st.sidebar:
        logo = _icon_data_uri()
        if logo:
            st.markdown(
                f"""
                <div class="sidebar-brand">
                  <img src="{logo}" alt="RevuAgent" />
                  <strong>RevuAgent</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("### Navigation")
        page = st.radio(
            "Pages",
            pages,
            label_visibility="collapsed",
            key="nav_page",
        )
        st.markdown("---")
        runs = list_output_runs()
        st.caption(f"{len(runs)} run(s) dans outputs/")
        if st.session_state.get("selected_run"):
            st.caption(f"Actif : `{st.session_state['selected_run']}`")
        if st.button("Rafraîchir"):
            st.rerun()

    if page == "Lancer Partie 1":
        page_run_part1()
    elif page == "Lancer Partie 2":
        page_run_part2()
    else:
        page_report()


if __name__ == "__main__":
    main()
