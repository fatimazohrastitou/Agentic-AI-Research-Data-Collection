
def assess_data_quality(articles: list) -> list:
    checked = []
    for article in articles:
        missing = [field for field in ("title", "year", "doi", "abstract") if not article.get(field)]
        item = dict(article)
        item["metadata_completeness"] = round((4 - len(missing)) / 4, 2)
        item["missing_metadata"] = missing
        item["metadata_quality"] = "complete" if not missing else "incomplete"
        checked.append(item)
    return checked
