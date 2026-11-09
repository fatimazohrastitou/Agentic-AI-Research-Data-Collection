from pathlib import Path
from tools.pdf_parser import extract_pdf_text

folder = Path("outputs/pdf_test")
pdf_files = list(folder.glob("*.pdf"))

print(f"PDF files found: {len(pdf_files)}")
print("\n=== PDF PARSER TEST ===")

for pdf in pdf_files:
    try:
        text = extract_pdf_text(str(pdf))

        print("\nFile:", pdf.name)
        print("Characters extracted:", len(text))
        print("Has readable text:", bool(text.strip()))
        print("Preview:", text[:300].replace("\n", " "))

    except Exception as e:
        print("\nFile:", pdf.name)
        print("ERROR:", str(e))