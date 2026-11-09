"""
Build/repair Part 2 handoff using already downloaded local PDFs.
No OpenAlex retrieval, screening, or downloading is performed.

Run from project root:
python tools/build_part2_handoff.py --output-dir outputs/cybersecurity_in_iot

The script validates that a PDF has pages AND non-empty extracted text.
If the downloaded copy is empty/unreadable, it also checks outputs/pdf_test/
for a valid copy with the same filename.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

try:
    from tools.pdf_parser import extract_pdf_sections
except ModuleNotFoundError:
    from pdf_parser import extract_pdf_sections


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_pdf_paths(raw_path: str | None, output_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    if raw_path:
        raw = Path(raw_path)
        candidates.append(raw)
        candidates.append(output_dir / "full_texts" / raw.name)
        candidates.append(output_dir.parent / "pdf_test" / raw.name)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def parse_valid_pdf(paths: list[Path]) -> tuple[Path | None, dict[str, Any] | None, list[str]]:
    attempts: list[str] = []
    for path in paths:
        if not path.is_file():
            attempts.append(f"Missing: {path}")
            continue
        try:
            parsed = extract_pdf_sections(path)
            page_count = int(parsed.get("page_count") or 0)
            full_text = (parsed.get("full_text") or "").strip()
            if page_count <= 0:
                attempts.append(f"No pages detected: {path}")
                continue
            if not full_text:
                attempts.append(f"No selectable text extracted: {path}")
                continue
            return path, parsed, attempts
        except Exception as exc:
            attempts.append(f"{path}: {type(exc).__name__}: {exc}")
    return None, None, attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    handoff_path = output_dir / "part2_handoff.json"
    acquisition_path = output_dir / "pdf_acquisition_results.json"

    if not handoff_path.is_file():
        raise FileNotFoundError(f"Missing: {handoff_path}")
    if not acquisition_path.is_file():
        raise FileNotFoundError(f"Missing: {acquisition_path}")

    handoff = read_json(handoff_path, [])
    acquisition = read_json(acquisition_path, [])
    if not isinstance(handoff, list) or not isinstance(acquisition, list):
        raise TypeError("Handoff and acquisition results must both be JSON lists.")

    acquisition_by_id = {
        item.get("openalex_id"): item
        for item in acquisition
        if item.get("openalex_id")
    }

    backup_path = output_dir / "part2_handoff_before_pdf_enrichment.json"
    if not backup_path.exists():
        shutil.copy2(handoff_path, backup_path)

    stats = {
        "handoff_records": len(handoff),
        "pdf_downloaded": 0,
        "pdf_parsed": 0,
        "pdf_recovered_from_pdf_test": 0,
        "pdf_not_downloaded": 0,
        "pdf_parse_failed_or_empty": 0,
    }

    for article in handoff:
        acquisition_item = acquisition_by_id.get(article.get("openalex_id"), {})
        status = acquisition_item.get("status", "not_found_in_acquisition_results")

        article["pdf_acquisition_status"] = status
        article["pdf_parse_status"] = "not_attempted"
        article["full_text"] = ""
        article["sections"] = {}
        article["detected_headings"] = []
        article["structure_warnings"] = []
        article["pdf_page_count"] = 0
        article["pdf_character_count"] = 0
        article.pop("pdf_parse_error", None)

        if status != "downloaded":
            article["local_pdf_path"] = acquisition_item.get("local_pdf_path")
            stats["pdf_not_downloaded"] += 1
            continue

        stats["pdf_downloaded"] += 1
        candidates = candidate_pdf_paths(
            acquisition_item.get("local_pdf_path"), output_dir
        )
        valid_path, parsed, attempts = parse_valid_pdf(candidates)

        if parsed is None or valid_path is None:
            article["pdf_parse_status"] = "parse_failed_or_empty"
            article["pdf_parse_error"] = " | ".join(attempts)
            article["local_pdf_path"] = acquisition_item.get("local_pdf_path")
            stats["pdf_parse_failed_or_empty"] += 1
            continue

        article["local_pdf_path"] = str(valid_path)
        article["full_text"] = parsed.get("full_text", "")
        article["sections"] = parsed.get("sections", {})
        article["detected_headings"] = parsed.get("detected_headings", [])
        article["structure_warnings"] = parsed.get("structure_warnings", [])
        article["pdf_page_count"] = parsed.get("page_count", 0)
        article["pdf_character_count"] = parsed.get("character_count", 0)
        article["pdf_parse_status"] = "parsed"
        article["pdf_parser_note"] = parsed.get("section_detection_note", "")
        stats["pdf_parsed"] += 1

        expected_path = candidates[0] if candidates else None
        if expected_path and valid_path.resolve() != expected_path.resolve():
            if valid_path.parent.name.lower() == "pdf_test":
                stats["pdf_recovered_from_pdf_test"] += 1

    handoff_path.write_text(
        json.dumps(handoff, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_path = output_dir / "part2_handoff_pdf_summary.json"
    summary_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("=" * 60)
    print("PART 2 HANDOFF ENRICHMENT — VALIDATED")
    print("=" * 60)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print(f"\nUpdated: {handoff_path}")
    print(f"Backup:  {backup_path}")
    print(f"Summary: {summary_path}")
    print("\nA PDF is marked parsed only when it has pages and non-empty text.")
    print("No retrieval, screening, or PDF downloading was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
