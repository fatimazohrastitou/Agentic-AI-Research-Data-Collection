"""Convert the review manuscript Markdown into a downloadable PDF."""
from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF


class ReportPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def _clean(text: str) -> str:
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")
    # Keep latin-1 friendly content for core Helvetica.
    return text.encode("latin-1", "replace").decode("latin-1")


def _strip_md_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _clean(text)


def _write_block(pdf: ReportPDF, text: str, *, size: int = 10, style: str = "", color=(20, 24, 32), h: float = 5.5):
    content = _strip_md_inline(text)
    if not content:
        pdf.ln(2)
        return
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    # Soft-wrap very long tokens (URLs, etc.)
    content = re.sub(r"(\S{80})", r"\1 ", content)
    pdf.multi_cell(pdf.epw, h, content)


def markdown_to_pdf(markdown_text: str, output_path: str | Path) -> Path:
    """Render a simple but readable PDF from the manuscript markdown."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = ReportPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()

    for raw in (markdown_text or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            _write_block(pdf, line[2:], size=16, style="B", color=(18, 53, 91), h=8)
            pdf.ln(2)
            continue
        if line.startswith("## "):
            _write_block(pdf, line[3:], size=13, style="B", color=(6, 122, 99), h=7)
            pdf.ln(1)
            continue
        if line.startswith("### "):
            _write_block(pdf, line[4:], size=11, style="B", color=(228, 87, 46), h=6)
            pdf.ln(1)
            continue

        if line.lstrip().startswith("- "):
            _write_block(pdf, "- " + line.lstrip()[2:], size=10, h=5.5)
        else:
            _write_block(pdf, line, size=10, h=5.5)

    pdf.output(str(output_path))
    return output_path


def write_manuscript_pdf(markdown_path: str | Path, pdf_path: str | Path | None = None) -> Path:
    markdown_path = Path(markdown_path)
    if pdf_path is None:
        pdf_path = markdown_path.with_suffix(".pdf")
    text = markdown_path.read_text(encoding="utf-8")
    return markdown_to_pdf(text, pdf_path)
