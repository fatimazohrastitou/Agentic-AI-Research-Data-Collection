"""Transparent title/abstract and publication-type pre-screening.

Automated decisions are preliminary triage only and always require human review.
"""
import re


def _normalise_terms(terms):
    return [str(t).strip().lower().replace("_", "-") for t in (terms or []) if str(t).strip()]


def _hits(text, terms):
    text = (text or "").lower()
    return [term for term in terms if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)]


def _normalise_type(value):
    value = re.sub(r"[-_\s]+", "-", str(value or "").strip().lower())
    aliases = {
        "conference-paper": "proceedings-article",
        "conference-article": "proceedings-article",
        "book-chapter": "book-chapter",
        "review-article": "review",
        "editorial-material": "editorial",
    }
    return aliases.get(value, value)


def screen_title_abstract(articles, inclusion_criteria=None, exclusion_criteria=None,
                          include_types=None, exclude_types=None):
    """Screen by keyword criteria and explicit publication-type criteria.

    The default policy accepts articles, reviews, proceedings/conference papers,
    book chapters and other non-excluded types. Letters and editorials are excluded
    by default. Supplying include_types activates an explicit allow-list.
    """
    include_terms = _normalise_terms(inclusion_criteria)
    exclude_terms = _normalise_terms(exclusion_criteria)
    include_type_set = {_normalise_type(x) for x in (include_types or []) if str(x).strip()}
    if not exclude_types:
        exclude_types = ["letter", "editorial"]
    exclude_type_set = {_normalise_type(x) for x in exclude_types if str(x).strip()}
    screened = []

    for article in articles:
        title = article.get("title") or ""
        abstract = article.get("abstract") or ""
        text = f"{title} {abstract}"
        original_type = article.get("type") or "unknown"
        publication_type = _normalise_type(original_type)
        include_hits = _hits(text, include_terms)
        exclude_hits = _hits(text, exclude_terms)
        type_excluded = publication_type in exclude_type_set
        type_not_allowed = bool(include_type_set) and publication_type not in include_type_set

        if type_excluded:
            decision = "exclude"
            reason = f"Publication type excluded by protocol: {original_type}."
            exclusion_category = "publication_type"
        elif type_not_allowed:
            decision = "exclude"
            reason = f"Publication type is not in the allowed types: {original_type}."
            exclusion_category = "publication_type"
        elif exclude_hits:
            decision = "exclude"
            reason = "Potential exclusion keyword(s) matched: " + ", ".join(exclude_hits)
            exclusion_category = "keyword"
        elif not abstract.strip():
            decision = "uncertain"
            reason = "Abstract unavailable; title-only assessment is insufficient. Human review required."
            exclusion_category = None
        elif include_terms and include_hits:
            decision = "potentially_include"
            reason = "Potential inclusion keyword(s) matched: " + ", ".join(include_hits)
            exclusion_category = None
        elif include_terms:
            decision = "uncertain"
            reason = "No inclusion keyword matched; semantic relevance cannot be ruled out. Human review required."
            exclusion_category = None
        else:
            decision = "needs_human_review"
            reason = "No explicit inclusion criteria supplied; human screening required."
            exclusion_category = None

        item = dict(article)
        item.update({
            "title_abstract_decision": decision,
            "title_abstract_reason": reason,
            "screening_method": "transparent_keyword_and_publication_type_pre_screening_v5_3",
            "screening_inclusion_hits": include_hits,
            "screening_exclusion_hits": exclude_hits,
            "screening_type": original_type,
            "screening_type_excluded": bool(type_excluded or type_not_allowed),
            "screening_exclusion_category": exclusion_category,
            "human_review_required": True,
            "screening_is_final": False,
        })
        screened.append(item)
    return screened
