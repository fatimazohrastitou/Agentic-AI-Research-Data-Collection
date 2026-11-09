"""
PDF text and section parser V2.2
--------------------------------
Extracts complete PDF text and detects section headings using:
- exact and numbered heading aliases;
- typography (bold / larger font) as supporting evidence;
- English and common Russian heading labels;
- conservative filtering to avoid treating body text, figures and tables as sections.

Important:
Heading detection is heuristic. The parser always preserves full_text, even when
section detection is incomplete. It does not use OCR.
"""

from __future__ import annotations

import re
import statistics
from pathlib import Path
from typing import Any

try:
    import pymupdf as fitz
except ImportError:  # Compatibility with older installations
    import fitz


# Canonical section names expected by downstream processing.
SECTION_ALIASES = {
    "abstract": {
        "abstract", "summary", "executive summary",
        "аннотация", "реферат",
    },
    "introduction": {
        "introduction", "introductory remarks", "background and introduction",
        "введение",
    },
    "literature_review": {
        "literature review", "related work", "related studies",
        "review of literature", "background", "background on iot",
        "обзор литературы", "анализ литературы",
    },
    "methodology": {
        "methodology", "methods", "materials and methods", "research method",
        "research methodology", "method", "experimental setup",
        "research design", "методология исследования", "методы исследования",
    },
    "results": {
        "results", "findings", "experimental results", "evaluation results",
        "performance evaluation", "результаты",
    },
    "discussion": {
        "discussion", "discussion and recommendations",
        "results and discussion", "discussion of results",
        "обсуждение",
    },
    "conclusion": {
        "conclusion", "conclusions", "concluding remarks",
        "conclusion and future work", "conclusions and future work",
        "future work and conclusion", "выводы", "заключение",
    },
    "references": {
        "references", "bibliography", "works cited", "литература",
        "список литературы",
    },
}

# Headings that are meaningful but do not safely map to a standard IMRaD section.
OTHER_HEADING_ALIASES = {
    "system of digital competence",
    "task solution",
    "analysis",
    "cia triad",
    "information security threats in iot",
    "over of iot scope and iot architecture",
    "standards and protocols",
    "wireless protocols for internet of things",
    "testing methods",
    "testing methods of iot devices",
    "governance risk management and international standards",
    "compliance with ethical standards",
    "acknowledgment",
    "acknowledgements",
    "author",
    "интернет вещей",
    "стандарты и протоколы интернет вещей",
    "беспроводные протоколы для интернета вещей",
    "методы тестирования iot устройств",
}

CANONICAL_LOOKUP = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}

# Common Roman numerals used in section numbering.
ROMAN = r"(?:[IVXLCDM]{1,7})"


def _clean_line(text: str) -> str:
    """Normalize whitespace while preserving meaningful punctuation."""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n:;.-")


def _normalize_heading(text: str) -> str:
    """Normalize a candidate heading for alias comparison."""
    value = _clean_line(text).lower()
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"^[\s\W]*", "", value)
    # Remove common section numbering: 2., 2.1, IV., I, etc.
    value = re.sub(r"^(?:(?:\d+(?:\.\d+)*|[ivxlcdm]{1,7})\s*[\.)\-:]?\s+)", "", value)
    value = re.sub(r"[\s\-–—:;,.]+$", "", value)
    value = re.sub(r"[\s\-–—]+", " ", value)
    return value.strip()


def _is_numbered_heading(text: str) -> bool:
    text = _clean_line(text)
    return bool(re.match(
        rf"^(?:\d+(?:\.\d+)*|{ROMAN})\s*[\.)\-:]?\s+\S",
        text,
        flags=re.IGNORECASE,
    ))


def _is_probable_heading(line: str, font_size: float, is_bold: bool,
                         median_font_size: float) -> bool:
    """Typography and shape are supporting signals, not sufficient alone."""
    text = _clean_line(line)
    if not text or len(text) > 135:
        return False

    # Reject obvious captions, table cells, URLs, and long prose.
    low = text.lower()
    if re.match(r"^(fig(?:ure)?|table)\s*[\d.]", low):
        return False
    if "http://" in low or "https://" in low or "www." in low:
        return False
    if len(text.split()) > 16:
        return False

    normalized = _normalize_heading(text)
    if normalized in CANONICAL_LOOKUP or normalized in OTHER_HEADING_ALIASES:
        return True

    numbered = _is_numbered_heading(text)
    uppercase = text.isupper() and len(text.split()) >= 2
    larger = font_size >= median_font_size + 1.0
    title_like = (
        len(text.split()) <= 12
        and text[:1].isupper()
        and not re.search(r"[.!?]$", text)
    )

    # Numbered headings can be regular-weight in some publisher PDFs.
    if numbered:
        # Numbered body sentences often begin with "1.". Keep only short,
        # heading-like lines; reject prose fragments and sentence punctuation.
        words = len(text.split())
        sentence_like = bool(re.search(r"[.!?]$", text)) or text.count(",") >= 1
        if words <= 9 and len(text) <= 95 and not sentence_like:
            return True
        return False

    # Roman-numeral headings such as "II. ИНТЕРНЕТ ВЕЩЕЙ" are often uppercase.
    roman_numbered = bool(re.match(rf"^{ROMAN}\s*[.)]?\s+\S", text, re.I))
    if roman_numbered and uppercase and len(text.split()) <= 10:
        return True

    # Unnumbered headings require stronger typographic evidence.
    if (is_bold or larger) and uppercase:
        return len(text.split()) <= 10 and not re.search(r"[,;]$", text)

    return False


def _canonical_section(heading: str) -> str | None:
    normalized = _normalize_heading(heading)
    if normalized in CANONICAL_LOOKUP:
        return CANONICAL_LOOKUP[normalized]
    # Some journals place the abstract label and its text on the same line.
    if re.match(r"^abstract\\s*[—–-]", heading.strip(), re.I):
        return "abstract"
    if re.match(r"^аннотация\\s*[—–-]", heading.strip(), re.I):
        return "abstract"
    return None


def _extract_pdf_lines(doc) -> tuple[list[dict[str, Any]], str]:
    """Extract ordered lines with page and typography metadata."""
    raw_lines: list[dict[str, Any]] = []
    page_texts: list[str] = []
    font_sizes: list[float] = []

    for page_number, page in enumerate(doc, start=1):
        page_text = page.get_text("text") or ""
        page_texts.append(page_text)

        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                spans = line.get("spans", [])
                text = _clean_line("".join(span.get("text", "") for span in spans))
                if not text:
                    continue

                sizes = [float(s.get("size", 0)) for s in spans if s.get("text", "").strip()]
                flags = [int(s.get("flags", 0)) for s in spans if s.get("text", "").strip()]
                size = max(sizes) if sizes else 0.0
                # PyMuPDF font flag bit 4 means bold.
                bold = any(flag & 16 for flag in flags)

                if size > 0:
                    font_sizes.append(size)

                raw_lines.append({
                    "text": text,
                    "page": page_number,
                    "font_size": size,
                    "bold": bold,
                    "y": float(line.get("bbox", [0, 0, 0, 0])[1]),
                })

    median_size = statistics.median(font_sizes) if font_sizes else 10.0
    for item in raw_lines:
        item["median_font_size"] = median_size

    return raw_lines, "\n".join(page_texts).strip()


def _detect_headings(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect likely headings and stop at the References/Bibliography section."""
    detected: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    for item in lines:
        text = item["text"]
        low = text.lower().strip()

        # Bibliography entries can look like bold/numbered headings.
        # Once References begins, do not classify anything after it as a heading.
        if _canonical_section(text) == "references":
            detected.append({
                "heading": text,
                "normalized_heading": _normalize_heading(text),
                "section": "references",
                "page": item["page"],
                "font_size": round(item["font_size"], 2),
                "bold": item["bold"],
            })
            break

        # Filter common non-heading fragments and obvious body/citation text.
        if (
            "student will" in low
            or re.match(r"^\d+\s*\[\d+\]$", text)
            or re.match(r"^(issn|doi|copyright|published online)\b", low)
            or re.search(r"\b(pp?\.|vol\.|no\.|issue)\s*\d", low)
        ):
            continue

        if not _is_probable_heading(
            text, item["font_size"], item["bold"], item["median_font_size"]
        ):
            continue

        if re.fullmatch(r"(?:\d+(?:\.\d+)*|[IVXLCDM]{1,7})[.)]?", text, re.I):
            continue

        normalized = _normalize_heading(text)
        key = (item["page"], normalized)
        if key in seen:
            continue
        seen.add(key)

        detected.append({
            "heading": text,
            "normalized_heading": normalized,
            "section": _canonical_section(text) or "other",
            "page": item["page"],
            "font_size": round(item["font_size"], 2),
            "bold": item["bold"],
        })

    return detected


def _slugify_heading(text: str) -> str:
    """Create a stable key for a non-standard section heading."""
    value = _normalize_heading(text).lower()
    value = re.sub(r"[^a-z0-9а-яё]+", "_", value, flags=re.IGNORECASE)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unnamed_section"


def _build_sections(full_text: str, headings: list[dict[str, Any]],
                    lines: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Keep every detected heading as an independent section.
    Standard headings retain canonical keys; topic-specific headings get
    readable slug keys. Full text remains available independently.
    """
    if not headings:
        return {}

    text_lines = [item["text"] for item in lines]
    positions: list[tuple[int, dict[str, Any]]] = []
    cursor = 0

    for heading in headings:
        target = heading["heading"]
        found = None
        for idx in range(cursor, len(text_lines)):
            if text_lines[idx] == target:
                found = idx
                cursor = idx + 1
                break
        if found is not None:
            positions.append((found, heading))

    sections: dict[str, Any] = {}
    used_keys: set[str] = set()

    for index, (line_index, heading) in enumerate(positions):
        next_line_index = (
            positions[index + 1][0]
            if index + 1 < len(positions)
            else len(text_lines)
        )
        content = "\n".join(text_lines[line_index + 1:next_line_index]).strip()
        if not content:
            continue

        canonical = heading["section"]
        base_key = canonical if canonical != "other" else _slugify_heading(heading["heading"])
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}_{suffix}"
            suffix += 1
        used_keys.add(key)

        # Keep section values as plain text for compatibility with downstream code.
        sections[key] = content

    return sections


def get_pdf_structure_summary(pdf_path: str | Path) -> dict[str, Any]:
    """Return a compact structural summary for one PDF."""
    result = extract_pdf_sections(pdf_path)
    return {
        "file_name": result["file_name"],
        "page_count": result["page_count"],
        "character_count": result["character_count"],
        "sections_found": list(result["sections"].keys()),
        "detected_headings": result["detected_headings"],
        "section_character_counts": {
            key: len(value.get("text", "")) if isinstance(value, dict) else len(value)
            for key, value in result["sections"].items()
        },
        "structure_warnings": result["structure_warnings"],
        "section_detection_note": result["section_detection_note"],
    }


def extract_pdf_sections(pdf_path: str | Path) -> dict[str, Any]:
    """
    Extract full text and best-effort sections from a PDF.

    Returns:
        file_name, page_count, character_count, full_text, sections,
        detected_headings, section_character_counts, structure_warnings,
        section_detection_note
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    with fitz.open(path) as doc:
        lines, full_text = _extract_pdf_lines(doc)
        page_count = len(doc)

    headings = _detect_headings(lines)
    sections = _build_sections(full_text, headings, lines)

    warnings: list[str] = []
    if not headings:
        warnings.append("No reliable section headings detected.")
    if len(headings) <= 1 and page_count > 3:
        warnings.append("Very few headings detected for a multi-page document.")

    abstract = sections.get("abstract", {})
    references = sections.get("references", {})
    abstract_text = abstract.get("text", "") if isinstance(abstract, dict) else str(abstract)
    references_text = references.get("text", "") if isinstance(references, dict) else str(references)
    if len(abstract_text) > max(12000, int(len(full_text) * 0.45)):
        warnings.append("Abstract section may contain text beyond the abstract.")
    if len(references_text) > len(full_text) * 0.65:
        warnings.append("References section may contain non-reference content.")

    section_counts = {
        key: len(value.get("text", "")) if isinstance(value, dict) else len(value)
        for key, value in sections.items()
    }

    note = (
        "Heuristic heading detection; verify section boundaries manually. "
        "Full text is preserved. No OCR is performed."
    )

    return {
        "file_name": path.name,
        "page_count": page_count,
        "character_count": len(full_text),
        "full_text": full_text,
        "sections": sections,
        "sections_found": list(sections.keys()),
        "detected_headings": headings,
        "section_character_counts": section_counts,
        "structure_warnings": warnings,
        "section_detection_note": note,
    }


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Backward-compatible helper returning only the complete extracted text."""
    result = extract_pdf_sections(pdf_path)
    return result["full_text"]
