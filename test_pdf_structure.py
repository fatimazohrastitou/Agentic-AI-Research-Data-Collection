from pathlib import Path
from tools.pdf_parser import extract_pdf_text
import re

folder = Path("outputs/pdf_test")
pdf_files = list(folder.glob("*.pdf"))

sections = {
    "Abstract": [r"\babstract\b", r"\br[ée]sum[ée]\b"],
    "Introduction": [r"\bintroduction\b", r"\b1\.\s*introduction\b"],
    "Methodology": [
        r"\bmethodology\b",
        r"\bmethods\b",
        r"\bmaterials and methods\b",
        r"\bresearch method\b"
    ],
    "Results": [r"\bresults\b", r"\bfindings\b"],
    "Discussion": [r"\bdiscussion\b"],
    "Conclusion": [r"\bconclusion\b", r"\bconclusions\b"]
}

print("=== PDF STRUCTURE TEST ===")

for pdf in pdf_files:
    text = extract_pdf_text(str(pdf))
    normalized = re.sub(r"\s+", " ", text.lower())

    print("\n" + "=" * 60)
    print("File:", pdf.name)
    print("Characters:", len(text))

    for section, patterns in sections.items():
        found = any(
            re.search(pattern, normalized, re.IGNORECASE)
            for pattern in patterns
        )
        print(f"{section}: {'FOUND' if found else 'NOT FOUND'}")