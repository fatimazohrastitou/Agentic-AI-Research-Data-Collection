from pathlib import Path
from tools.pdf_parser import get_pdf_structure_summary

folder = Path("outputs/pdf_test")

for pdf in folder.glob("*.pdf"):
    try:
        result = get_pdf_structure_summary(str(pdf))

        print("\n" + "=" * 60)
        print("File:", result["file_name"])
        print("Pages:", result["page_count"])
        print("Characters:", result["character_count"])
        print("Sections:", result["sections_found"])

        for section, count in result["section_character_counts"].items():
            print(f"{section}: {count} characters")

    except Exception as e:
        print("ERROR:", pdf.name, str(e))
print("\nDETECTED HEADINGS:")
for heading in result["detected_headings"]:
    print(
        heading["page"],
        heading["section"],
        "->",
        heading["heading"]
    )

print("\nSTRUCTURE WARNINGS:")
for warning in result["structure_warnings"]:
    print("-", warning)
