from pathlib import Path
import json
from tools.openalex_tool import search_openalex


def retrieve_literature(strategy: dict, protocol: dict, max_results: int = 100) -> list:
    date_range = protocol.get("date_range", {})
    databases = strategy.get("databases", [])
    queries = []
    for database in databases:
        query = (database.get("query") or "").strip()
        if query and query not in queries:
            queries.append(query)
    if not queries:
        raise ValueError("Search strategy contains no usable OpenAlex query")

    # Distribute the requested limit across distinct query formulations, then merge.
    per_query = max(1, (int(max_results) + len(queries) - 1) // len(queries))
    collected, seen = [], set()
    for query in queries:
        batch = search_openalex(
            query=query,
            max_results=per_query,
            year_from=date_range.get("from"),
            year_to=date_range.get("to")
        )
        for article in batch:
            key = (article.get("doi") or article.get("openalex_id") or article.get("title", "")).lower()
            if key and key not in seen:
                seen.add(key)
                article["retrieval_query"] = query
                collected.append(article)
    return collected[:int(max_results)]


def save_retrieved(articles: list, path="data/retrieved_articles/articles_raw.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
