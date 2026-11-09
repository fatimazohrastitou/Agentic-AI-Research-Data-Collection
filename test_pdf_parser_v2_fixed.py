from pathlib import Path
from tools.pdf_parser import get_pdf_structure_summary

folder = Path("outputs/pdf_test")
pdf_files = sorted(folder.glob("*.pdf"))

if not pdf_files:
    print(f"No PDF files found in: {folder.resolve()}")
    raise SystemExit(0)

for pdf in pdf_files:
    print("\\n" + "=" * 75)
    print("FILE:", pdf.name)

    try:
        result = get_pdf_structure_summary(str(pdf))

        print("Pages:", result["page_count"])
        print("Characters:", result["character_count"])
        print("Sections:", result.get("sections_found", []))

        print("\\nSECTION CHARACTER COUNTS:")
        for section, count in result.get("section_character_counts", {}).items():
            print(f"  - {section}: {count:,} characters")

        print("\\nDETECTED HEADINGS:")
        headings = result.get("detected_headings", [])
        if headings:
            for heading in headings:
                print(
                    f"  Page {heading.get('page', '?')} | "
                    f"{heading.get('section', 'unknown')} | "
                    f"{heading.get('heading', '')}"
                )
        else:
            print("  No headings detected.")

        print("\\nSTRUCTURE WARNINGS:")
        warnings = result.get("structure_warnings", [])
        if warnings:
            for warning in warnings:
                print("  -", warning)
        else:
            print("  No warnings.")

    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))

print("\\n" + "=" * 75)
print(f"Finished. PDFs tested: {len(pdf_files)}")
