import re
import unicodedata


def normalize_title(title: str) -> str:
    value = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", value.lower())


def deduplicate_articles(articles: list):
    seen_doi, seen_title = set(), set()
    unique, duplicates = [], []
    for article in articles:
        doi = (article.get("doi") or "").lower().replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        title_key = normalize_title(article.get("title", ""))
        reason = None
        if doi and doi in seen_doi:
            reason = "duplicate_doi"
        elif title_key and title_key in seen_title:
            reason = "duplicate_title"
        if reason:
            duplicates.append({"article": article, "duplicate_reason": reason})
            continue
        if doi:
            seen_doi.add(doi)
        if title_key:
            seen_title.add(title_key)
        unique.append(article)
    return unique, duplicates
