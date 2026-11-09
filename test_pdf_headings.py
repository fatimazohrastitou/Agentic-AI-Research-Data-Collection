"""Inspect likely section headings in PDFs using text and font styling.

Run from the project root:
    python test_pdf_headings.py

Scans outputs/pdf_test/*.pdf and prints page number, font size, bold flag,
and candidate heading text. This is diagnostic only; it does not modify PDFs.
"""
from pathlib import Path
import re

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


PDF_FOLDER = Path("outputs/pdf_test")
MAX_HEADING_LENGTH = 120


def is_candidate(text, size, median_size, bold):
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > MAX_HEADING_LENGTH:
        return False

    # Exclude common running headers/footers and lines that look like sentences.
    if len(text) > 90 and text.endswith((".", ",", ";")):
        return False

    numbered = bool(re.match(
        r"^(?:(?:\d+(?:\.\d+)*|[IVXLC]+)[.)]?)\s+\S+", text, re.I
    ))
    uppercase = (
        any(ch.isalpha() for ch in text)
        and text == text.upper()
    )
    title_like = (
        sum(ch.isalpha() for ch in text) > 3
        and text == text.title()
    )
    larger_font = median_size > 0 and size >= median_size * 1.08

    return numbered or bold or larger_font or uppercase or title_like


def inspect_pdf(pdf_path):
    candidates = []

    with pymupdf.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            page_dict = page.get_text("dict")
            raw_lines = []

            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    text = "".join(span.get("text", "") for span in spans)
                    text = re.sub(r"\s+", " ", text).strip()
                    if not text:
                        continue

                    sizes = [float(s.get("size", 0)) for s in spans]
                    size = max(sizes, default=0.0)
                    bold = any(
                        "bold" in s.get("font", "").lower()
                        or bool(int(s.get("flags", 0)) & 16)
                        for s in spans
                    )
                    raw_lines.append({
                        "text": text,
                        "size": size,
                        "bold": bold,
                    })

            page_sizes = sorted(
                item["size"] for item in raw_lines if item["size"] > 0
            )
            median_size = page_sizes[len(page_sizes) // 2] if page_sizes else 0

            for item in raw_lines:
                if is_candidate(
                    item["text"], item["size"], median_size, item["bold"]
                ):
                    candidates.append({
                        "page": page_number,
                        **item,
                    })

    return candidates


def main():
    if not PDF_FOLDER.exists():
        raise FileNotFoundError(
            f"Folder not found: {PDF_FOLDER.resolve()}\n"
            "Make sure you run this script from the project root."
        )

    pdfs = sorted(PDF_FOLDER.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in: {PDF_FOLDER.resolve()}")
        return

    print(f"PDF files found: {len(pdfs)}")

    for pdf in pdfs:
        print("\n" + "=" * 90)
        print(f"FILE: {pdf.name}")
        print("-" * 90)

        try:
            candidates = inspect_pdf(pdf)
            if not candidates:
                print("No likely headings detected.")
                continue

            for item in candidates:
                style = "BOLD" if item["bold"] else "regular"
                print(
                    f"Page {item['page']:>2} | "
                    f"{item['size']:>5.1f} pt | "
                    f"{style:<7} | {item['text']}"
                )
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
