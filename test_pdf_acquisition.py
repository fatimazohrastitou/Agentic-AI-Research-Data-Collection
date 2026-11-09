import json
from pathlib import Path
from tools.pdf_acquisition import acquire_open_pdfs

# آخر نتائج البحث
articles_file = Path("outputs/cybersecurity_in_iot/articles.json")

if not articles_file.exists():
    raise FileNotFoundError(f"File not found: {articles_file}")

with articles_file.open("r", encoding="utf-8") as f:
    articles = json.load(f)

# نفس شرط المشروع: لا نحمل المقالات المرفوضة
candidates = [
    article for article in articles
    if article.get("title_abstract_decision") != "exclude"
]

print(f"Articles loaded: {len(articles)}")
print(f"PDF candidates: {len(candidates)}")

results = acquire_open_pdfs(
    candidates,
    destination="outputs/pdf_test"
)

print("\n=== PDF ACQUISITION TEST ===")

for result in results:
    print(
        result.get("status"),
        "|",
        result.get("title", "Unknown title")
    )

print("\nTotal:", len(results))
print("Downloaded:", sum(r.get("status") == "downloaded" for r in results))