from pathlib import Path
import json
import re
import unicodedata

STOPWORDS = {
    # English
    "the", "and", "for", "with", "from", "about", "into", "using", "based",
    "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "are", "is", "was", "were", "be", "been", "being", "does", "do", "did",
    "can", "could", "would", "should", "will", "shall", "may", "might",
    "main", "major", "key", "role", "impact", "effect", "effects", "study",
    "studies", "research", "analysis", "approach", "approaches",
    # French
    "dans", "avec", "pour", "les", "des", "une", "un", "sur", "par", "de",
    "du", "la", "le", "et", "en", "est", "sont", "qui", "que", "quoi",
    "comment", "quel", "quelle", "quels", "quelles", "leur", "leurs",
    # Spanish / Portuguese
    "los", "las", "del", "por", "para", "con", "una", "uno", "das", "dos",
    "como", "sobre", "entre"
}

TOKEN_PATTERN = re.compile(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9-]*")

# Conservative, domain-agnostic lexical equivalents. This is deliberately
# editable and does not pretend to infer specialist terminology.
SYNONYM_LEXICON = {
    "cybersecurity": ["cyber security", "information security"],
    "security": ["protection", "information security"],
    "threat": ["risk", "attack", "cyber threat"],
    "threats": ["risks", "attacks", "cyber threats"],
    "attack": ["threat", "intrusion"],
    "attacks": ["threats", "intrusions", "cyber attacks"],
    "vulnerability": ["weakness", "security flaw"],
    "vulnerabilities": ["weaknesses", "security flaws"],
    "privacy": ["data privacy", "information privacy"],
    "detection": ["identification", "discovery"],
    "prevention": ["mitigation", "protection"],
    "mitigation": ["prevention", "risk reduction"],
    "risk": ["threat", "exposure"],
    "risks": ["threats", "exposures"],
    "performance": ["efficiency", "effectiveness"],
    "evaluation": ["assessment", "appraisal"],
    "framework": ["model", "architecture"],
    "frameworks": ["models", "architectures"],
    "renewable": ["sustainable"],
    "energy": ["power"],
    "deepfake": ["synthetic media", "manipulated media"],
    "detection": ["identification", "recognition"],
}

PHRASE_ALIASES = {
    "iot": ["internet of things"],
    "internet of things": ["iot"],
    "ai": ["artificial intelligence"],
    "artificial intelligence": ["ai"],
    "ml": ["machine learning"],
    "machine learning": ["ml"],
}


def _normalise_token(token: str) -> str:
    return unicodedata.normalize("NFKC", token).lower().strip("-")


def _extract_terms(text: str) -> list:
    terms = []
    for raw in TOKEN_PATTERN.findall(text or ""):
        term = _normalise_token(raw)
        if len(term) < 3 or term in STOPWORDS:
            continue
        if term not in terms:
            terms.append(term)
    return terms


def _clean_phrase(text: str) -> str:
    return " ".join(_extract_terms(text))


def _phrase_expansions(text: str) -> list:
    """Return known multi-word aliases for phrases explicitly present."""
    normalised = (text or "").lower()
    found = []
    for phrase, aliases in PHRASE_ALIASES.items():
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalised):
            for alias in aliases:
                if alias not in found:
                    found.append(alias)
    return found


def _build_synonym_groups(terms: list, original_text: str) -> list:
    groups = []
    seen = set()
    for term in terms:
        variants = [term] + SYNONYM_LEXICON.get(term, [])
        variants = list(dict.fromkeys(v for v in variants if v))
        if len(variants) > 1:
            key = tuple(variants)
            if key not in seen:
                groups.append({
                    "concept": term,
                    "preferred_term": term,
                    "synonyms": variants[1:],
                    "search_variants": variants
                })
                seen.add(key)

    for alias in _phrase_expansions(original_text):
        groups.append({
            "concept": "phrase_alias",
            "preferred_term": alias,
            "synonyms": [],
            "search_variants": [alias]
        })
    return groups


def _make_query_variants(base_terms: list, synonym_groups: list,
                         source_text: str = "", limit: int = 6) -> list:
    """
    Generate a bounded list of plain-text queries.

    Includes the base query, single-term synonym substitutions, and phrase
    aliases (for example, iot -> internet of things). The limit applies to
    each call; the final strategy applies a second global limit.
    """
    base = " ".join(base_terms).strip()
    queries = []
    if base:
        queries.append(base)

    # Synonym substitutions: replace one original term at a time.
    for group in synonym_groups:
        preferred = group.get("preferred_term", "")
        if preferred not in base_terms:
            continue
        for synonym in group.get("synonyms", []):
            candidate_terms = list(base_terms)
            candidate_terms[candidate_terms.index(preferred)] = synonym
            candidate = " ".join(candidate_terms).strip()
            if candidate and candidate not in queries:
                queries.append(candidate)
            if len(queries) >= limit:
                return queries[:limit]

    # Phrase aliases are replacements too, not metadata-only entries.
    for phrase, aliases in PHRASE_ALIASES.items():
        if not re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                         (source_text or "").lower()):
            continue
        phrase_tokens = _extract_terms(phrase)
        # Acronyms such as "iot" are represented by one base token.
        matched = next((t for t in phrase_tokens if t in base_terms), None)
        if matched is None and phrase in base_terms:
            matched = phrase
        if matched is None:
            continue
        for alias in aliases:
            candidate_terms = list(base_terms)
            candidate_terms[candidate_terms.index(matched)] = alias
            candidate = " ".join(candidate_terms).strip()
            if candidate and candidate not in queries:
                queries.append(candidate)
            if len(queries) >= limit:
                return queries[:limit]

    return queries[:limit]

def build_search_strategy(topic: str, research_question: str = "",
                          custom_synonyms: dict = None,
                          max_query_variants: int = 6) -> dict:
    """
    Generic search strategy builder.
    Optional custom_synonyms example:
      {"edge computing": ["edge-based computing", "edge systems"]}
    """
    topic = (topic or "").strip()
    research_question = (research_question or "").strip()
    if not topic:
        raise ValueError("Research topic cannot be empty")

    topic_terms = _extract_terms(topic)
    question_terms = _extract_terms(research_question)
    additional_question_terms = [
        term for term in question_terms if term not in topic_terms
    ]

    combined_terms = list(topic_terms)
    for term in additional_question_terms:
        if term not in combined_terms:
            combined_terms.append(term)

    lexicon = dict(SYNONYM_LEXICON)
    if custom_synonyms:
        for key, values in custom_synonyms.items():
            if isinstance(values, str):
                values = [values]
            lexicon[_clean_phrase(key)] = list(values)

    # Use a local copy of the lexicon to support user-provided terms.
    def groups_for(terms, source_text):
        groups = []
        for term in terms:
            variants = [term] + lexicon.get(term, [])
            variants = list(dict.fromkeys(v for v in variants if v))
            if len(variants) > 1:
                groups.append({
                    "concept": term,
                    "preferred_term": term,
                    "synonyms": variants[1:],
                    "search_variants": variants
                })
        for alias in _phrase_expansions(source_text):
            groups.append({
                "concept": "phrase_alias",
                "preferred_term": alias,
                "synonyms": [],
                "search_variants": [alias]
            })
        return groups

    topic_groups = groups_for(topic_terms, topic)
    combined_groups = groups_for(combined_terms, topic + " " + research_question)

    # Build topic and topic+question candidates, then enforce one global cap.
    topic_queries = _make_query_variants(
        topic_terms, topic_groups, topic, max_query_variants
    )
    combined_queries = _make_query_variants(
        combined_terms, combined_groups, topic + " " + research_question,
        max_query_variants
    )

    # Preserve both core queries first, then add the most useful variants.
    ordered_candidates = []
    if topic_queries:
        ordered_candidates.append((topic_queries[0], "topic_core"))
    if combined_queries and combined_queries[0] != (topic_queries[0] if topic_queries else None):
        ordered_candidates.append((combined_queries[0], "topic_plus_question"))

    for query in topic_queries[1:]:
        ordered_candidates.append((query, "topic_synonym_variant"))
    for query in combined_queries[1:]:
        ordered_candidates.append((query, "question_synonym_variant"))

    databases = []
    seen_queries = set()
    for query, role in ordered_candidates:
        normalized = " ".join(query.lower().split())
        if not normalized or normalized in seen_queries:
            continue
        seen_queries.add(normalized)
        databases.append({
            "name": "OpenAlex",
            "query": query,
            "search_field": "OpenAlex searchable work metadata",
            "query_role": role
        })
        if len(databases) >= max(1, int(max_query_variants)):
            break

    concept_groups = []
    if topic_terms:
        concept_groups.append({
            "concept": "topic",
            "terms": topic_terms,
            "synonym_groups": topic_groups
        })
    if additional_question_terms:
        concept_groups.append({
            "concept": "research_question",
            "terms": additional_question_terms,
            "synonym_groups": groups_for(
                additional_question_terms, research_question
            )
        })

    boolean_groups = []
    for group in concept_groups:
        terms = []
        for term in group["terms"]:
            terms.append(f'"{term}"')
        for synonym_group in group.get("synonym_groups", []):
            terms.extend(f'"{s}"' for s in synonym_group["synonyms"])
        # Include phrase aliases that belong to a term in this concept group.
        source_for_aliases = topic if group["concept"] == "topic" else research_question
        for phrase, aliases in PHRASE_ALIASES.items():
            if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)",
                         source_for_aliases.lower()):
                terms.extend(f'"{alias}"' for alias in aliases)
        terms = list(dict.fromkeys(terms))
        if terms:
            boolean_groups.append("(" + " OR ".join(terms) + ")")

    return {
        "topic": topic,
        "research_question": research_question,
        "databases": databases,
        "keywords": combined_terms,
        "topic_keywords": topic_terms,
        "question_keywords": additional_question_terms,
        "concept_groups": concept_groups,
        "boolean_query_template": " AND ".join(boolean_groups),
        "synonym_expansion": {
            "enabled": True,
            "method": "conservative_editable_lexicon",
            "lexicon_version": "1.1",
            "custom_synonyms_supplied": bool(custom_synonyms),
            "warning": (
                "Synonyms are candidate search terms, not guaranteed equivalents. "
                "A researcher must validate each term for the specific topic."
            )
        },
        "notes": (
            "Generic stopword removal and conservative synonym expansion are applied. "
            "OpenAlex receives a globally capped set of separate plain-text query variants; phrase aliases are included in query generation. The Boolean query "
            "is an editable protocol template and is not sent as Boolean syntax to OpenAlex. "
            "Review synonyms, spelling variants, controlled vocabulary, and database-specific "
            "syntax before finalizing the protocol."
        ),
        "generation_method": "generic_token_extraction_synonym_and_phrase_alias_expansion_no_llm",
        "version": "2.2"
    }


def save_strategy(strategy: dict, path="data/search_strategy/search_strategy.json"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(strategy, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return path
