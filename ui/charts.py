"""Colorful Plotly charts for the Streamlit UI."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DECISION_COLORS = {
    "potentially_include": "#0b6e4f",
    "include": "#0b6e4f",
    "uncertain": "#c47d1a",
    "needs_human_review": "#c47d1a",
    "exclude": "#b42318",
    "unknown": "#5c6670",
}

BAND_COLORS = {
    "high": "#0b6e4f",
    "medium": "#c47d1a",
    "low": "#16324f",
}

FUNNEL_COLORS = ["#16324f", "#1f6f8b", "#0b6e4f", "#2a9d8f", "#c47d1a", "#b85c38"]


def _apply_layout(fig: go.Figure, *, height: int = 340, **extra) -> go.Figure:
    """Apply layout via a single dict to avoid duplicate kwargs with Plotly 7."""
    layout = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Manrope, sans-serif", "color": "#0c1220", "size": 13},
        "margin": {"l": 10, "r": 10, "t": 40, "b": 10},
        "height": height,
    }
    layout.update(extra)
    fig.update_layout(layout)
    return fig


def _counts_df(mapping: dict[str, int], key: str) -> pd.DataFrame:
    rows = [{key: str(k), "n": int(v)} for k, v in (mapping or {}).items()]
    return pd.DataFrame(rows)


def decision_donut(decisions: dict[str, int], title: str = "Decisions screening") -> go.Figure:
    df = _counts_df(decisions, "decision")
    fig = go.Figure()
    if not df.empty:
        colors = [DECISION_COLORS.get(d, "#5c6670") for d in df["decision"]]
        fig.add_trace(
            go.Pie(
                labels=df["decision"],
                values=df["n"],
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="#fff7ef", width=2)),
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value} articles<extra></extra>",
                sort=False,
            )
        )
        fig.update_traces(rotation=90)
    return _apply_layout(fig, title=title, showlegend=False)


def band_bars(bands: dict[str, int], title: str = "Pertinence") -> go.Figure:
    df = _counts_df(bands, "band")
    fig = go.Figure()
    if not df.empty:
        order = ["high", "medium", "low"]
        df["band"] = pd.Categorical(df["band"], categories=order, ordered=True)
        df = df.sort_values("band")
        colors = [BAND_COLORS.get(str(b), "#5c6670") for b in df["band"]]
        fig.add_trace(
            go.Bar(
                x=df["band"].astype(str),
                y=df["n"],
                marker=dict(color=colors, line=dict(width=0)),
                text=df["n"],
                textposition="outside",
                hovertemplate="%{x}<br>%{y} articles<extra></extra>",
            )
        )
    return _apply_layout(
        fig,
        title=title,
        xaxis_title="",
        yaxis_title="Articles",
        yaxis={"gridcolor": "rgba(16,24,32,0.08)"},
    )


def prisma_funnel_chart(prisma: dict[str, Any], title: str = "Entonnoir PRISMA") -> go.Figure:
    steps = [
        ("Identifies", prisma.get("records_identified")),
        ("Apres dedup", prisma.get("records_after_deduplication")),
        ("Screening P1", prisma.get("records_screened_title_abstract")),
        ("Handoff", prisma.get("needs_human_review")),
        ("Full-text", prisma.get("fulltext_assessed")),
        ("Inclus", prisma.get("records_included")),
    ]
    labels, values = [], []
    for label, value in steps:
        if value is None:
            continue
        labels.append(label)
        values.append(int(value))
    fig = go.Figure()
    if values:
        colors = FUNNEL_COLORS[: len(values)]
        fig.add_trace(
            go.Funnel(
                y=labels,
                x=values,
                textinfo="value+percent initial",
                marker=dict(color=colors, line=dict(width=1, color="#fff7ef")),
                connector=dict(line=dict(color="#d9d1c4", width=2)),
                hovertemplate="%{y}<br>%{x} records<extra></extra>",
            )
        )
    return _apply_layout(fig, height=380, title=title)


def relevance_scatter(records: list[dict], title: str = "Score de pertinence") -> go.Figure:
    rows = []
    for item in records or []:
        score = item.get("relevance_score")
        if score is None:
            continue
        rows.append({
            "title": (item.get("title") or "")[:70],
            "year": item.get("year") or 0,
            "score": float(score),
            "decision": item.get("title_abstract_decision") or "unknown",
            "band": item.get("relevance_band") or "low",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return _apply_layout(go.Figure(), title=title)

    fig = px.scatter(
        df,
        x="year",
        y="score",
        color="decision",
        color_discrete_map=DECISION_COLORS,
        hover_name="title",
        title=title,
    )
    fig.update_traces(marker=dict(size=12, line=dict(width=1, color="#fff7ef"), opacity=0.9))
    return _apply_layout(
        fig,
        height=360,
        xaxis_title="Annee",
        yaxis_title="Relevance score",
        yaxis={"range": [-0.05, 1.05], "gridcolor": "rgba(16,24,32,0.08)"},
        xaxis={"gridcolor": "rgba(16,24,32,0.06)"},
        legend_title_text="Decision",
    )


def animated_year_decisions(records: list[dict], title: str = "Evolution par annee") -> go.Figure:
    rows = []
    for item in records or []:
        year = item.get("year")
        if not year:
            continue
        rows.append({
            "year": int(year),
            "decision": item.get("title_abstract_decision") or "unknown",
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return _apply_layout(go.Figure(), title=title)

    counts = df.groupby(["year", "decision"]).size().reset_index(name="n")
    fig = px.bar(
        counts,
        x="year",
        y="n",
        color="decision",
        color_discrete_map=DECISION_COLORS,
        title=title,
        barmode="stack",
    )
    fig.update_traces(marker_line_width=0)
    return _apply_layout(
        fig,
        height=360,
        xaxis_title="Annee",
        yaxis_title="Articles",
        yaxis={"gridcolor": "rgba(16,24,32,0.08)"},
        legend_title_text="Decision",
    )
