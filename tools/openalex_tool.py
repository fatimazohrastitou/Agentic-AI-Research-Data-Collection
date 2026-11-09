
import os
import time
import random
import requests

BASE_URL = "https://api.openalex.org/works"

MAX_RETRIES = 6
INITIAL_BACKOFF = 5
MAX_BACKOFF = 120


def reconstruct_abstract(inverted_index):
    if not inverted_index:
        return ""

    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[int(pos)] = word

    return " ".join(words[i] for i in sorted(words))


def request_openalex(params, headers, timeout=45):
    """
    Send an OpenAlex request with retry and exponential backoff.
    Handles HTTP 429 and temporary server errors.
    """

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                BASE_URL,
                params=params,
                headers=headers,
                timeout=timeout
            )

            if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                if attempt == MAX_RETRIES:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")

                if retry_after:
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        wait_time = min(
                            INITIAL_BACKOFF * (2 ** attempt),
                            MAX_BACKOFF
                        )
                else:
                    wait_time = min(
                        INITIAL_BACKOFF * (2 ** attempt),
                        MAX_BACKOFF
                    )

                wait_time += random.uniform(0, 2)

                print(
                    f"[OpenAlex] HTTP {response.status_code}. "
                    f"Retry {attempt + 1}/{MAX_RETRIES} "
                    f"after {wait_time:.1f} seconds..."
                )

                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES:
                raise

            wait_time = min(
                INITIAL_BACKOFF * (2 ** attempt),
                MAX_BACKOFF
            )

            print(
                f"[OpenAlex] Request timeout. "
                f"Retry {attempt + 1}/{MAX_RETRIES} "
                f"after {wait_time} seconds..."
            )

            time.sleep(wait_time)

        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES:
                raise

            wait_time = min(
                INITIAL_BACKOFF * (2 ** attempt),
                MAX_BACKOFF
            )

            print(
                f"[OpenAlex] Connection error. "
                f"Retry {attempt + 1}/{MAX_RETRIES} "
                f"after {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError("OpenAlex request failed after all retries.")


def search_openalex(
    query: str,
    max_results: int = 100,
    year_from=None,
    year_to=None,
    email=None,
    per_page: int = 100
):
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    max_results = max(1, min(int(max_results), 2000))

    filters = []

    if year_from:
        filters.append(
            f"from_publication_date:{int(year_from)}-01-01"
        )

    if year_to:
        filters.append(
            f"to_publication_date:{int(year_to)}-12-31"
        )

    params = {
        "search": query,
        "per-page": min(int(per_page), 100),
        "cursor": "*",
        "select": (
            "id,doi,title,publication_year,publication_date,type,"
            "language,authorships,primary_location,open_access,"
            "biblio,cited_by_count,abstract_inverted_index,ids"
        )
    }

    if filters:
        params["filter"] = ",".join(filters)

    openalex_email = email or os.getenv("OPENALEX_EMAIL")

    if openalex_email:
        params["mailto"] = openalex_email

    headers = {
        "User-Agent": (
            "AgenticSystematicReview/1.0 "
            "(educational research project)"
        )
    }

    results = []

    while len(results) < max_results:

        response = request_openalex(params, headers)
        payload = response.json()

        batch = payload.get("results", [])

        if not batch:
            break

        for item in batch:

            authorships = item.get("authorships") or []

            authors = [
                a.get("author", {}).get("display_name", "")
                for a in authorships
            ]

            primary = item.get("primary_location") or {}

            source = (
                primary.get("source") or {}
            ).get("display_name")

            open_access = item.get("open_access") or {}

            results.append({
                "openalex_id": item.get("id"),
                "doi": item.get("doi"),
                "title": item.get("title") or "",
                "year": item.get("publication_year"),
                "publication_date": item.get("publication_date"),
                "type": item.get("type"),
                "language": item.get("language"),
                "authors": authors,
                "venue": source,
                "abstract": reconstruct_abstract(
                    item.get("abstract_inverted_index")
                ),
                "cited_by_count": item.get("cited_by_count", 0),
                "is_oa": open_access.get("is_oa"),
                "landing_page_url": primary.get("landing_page_url"),
                "pdf_url": open_access.get("oa_url"),
                "source_database": "OpenAlex",
                "raw_ids": item.get("ids", {})
            })

            if len(results) >= max_results:
                break

        next_cursor = (
            payload.get("meta") or {}
        ).get("next_cursor")

        if not next_cursor:
            break

        params["cursor"] = next_cursor

        # Avoid sending requests too quickly.
        time.sleep(1.5)

    return results
