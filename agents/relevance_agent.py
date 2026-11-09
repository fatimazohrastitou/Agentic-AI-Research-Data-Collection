"""Local, explainable lexical relevance ranking (no LLM/API key required).

This is a prioritisation aid, NOT a semantic relevance classifier and never
makes final inclusion/exclusion decisions. It is topic-agnostic.
"""
import re
from collections import Counter

_STOPWORDS = {
    'the','and','for','with','from','about','into','using','based','this','that','are','was','were',
    'dans','avec','pour','les','des','une','un','sur','par','de','du','la','le','et','en','aux',
    'der','die','das','und','mit','von','für','ist','im','in','to','of','a','an','is','are',
    'what','which','who','how','why','when','where','main','major','role','impact'
}


def _normalise_token(token):
    """Small language-neutral normalisation; deliberately avoids domain vocabularies."""
    t = token.lower()
    if len(t) > 5 and t.endswith('ies'):
        return t[:-3] + 'y'
    if len(t) > 4 and t.endswith('s') and not t.endswith(('ss', 'us', 'is')):
        return t[:-1]
    return t


def _tokens(text):
    raw = re.findall(r"[A-Za-zÀ-ÿ0-9]+", str(text or '').lower())
    return [_normalise_token(t) for t in raw
            if len(t) > 2 and t not in _STOPWORDS]


def _phrase_present(phrase, text):
    phrase = ' '.join(_tokens(phrase))
    haystack = ' '.join(_tokens(text))
    return bool(phrase and phrase in haystack)


def score_relevance(articles, topic, research_question='', inclusion_criteria=None):
    """Score topic/question term coverage with title emphasis and explanations.

    Score components: 45% query-term coverage, 35% title coverage, 20% abstract
    coverage. Topic terms are weighted twice as much as question terms. A phrase
    match adds a small bounded bonus. Bands are conservative ranking buckets only (high >= 0.90, medium >= 0.70).
    """
    articles = list(articles or [])
    topic_terms = list(dict.fromkeys(_tokens(topic)))
    question_terms = list(dict.fromkeys(_tokens(research_question)))
    criteria_terms = list(dict.fromkeys(_tokens(' '.join(map(str, inclusion_criteria or [])))))

    # Preserve topic priority while still allowing question/criteria vocabulary.
    weights = Counter()
    for term in topic_terms:
        weights[term] += 2.0
    for term in question_terms:
        weights[term] += 1.0
    for term in criteria_terms:
        weights[term] += 1.0

    if not articles or not weights:
        return [dict(a, relevance_score=0.0, relevance_band='unscored',
                     relevance_method='local_weighted_lexical_v1', relevance_terms=[],
                     relevance_explanation='Insufficient query text for lexical ranking.') for a in articles]

    total_weight = sum(weights.values()) or 1.0
    scored = []
    for article in articles:
        title = str(article.get('title') or '')
        abstract = str(article.get('abstract') or '')
        title_set, abstract_set = set(_tokens(title)), set(_tokens(abstract))
        all_set = title_set | abstract_set

        query_coverage = sum(w for t, w in weights.items() if t in all_set) / total_weight
        title_coverage = sum(w for t, w in weights.items() if t in title_set) / total_weight
        abstract_coverage = sum(w for t, w in weights.items() if t in abstract_set) / total_weight
        score = 0.45 * query_coverage + 0.35 * title_coverage + 0.20 * abstract_coverage

        phrase_bonus = 0.0
        phrases = [topic, research_question]
        for phrase in phrases:
            p_terms = _tokens(phrase)
            if len(p_terms) >= 2 and _phrase_present(phrase, title):
                phrase_bonus = max(phrase_bonus, 0.08)
            elif len(p_terms) >= 2 and _phrase_present(phrase, abstract):
                phrase_bonus = max(phrase_bonus, 0.04)
        score = round(min(1.0, score + phrase_bonus), 4)

        matched = [t for t in weights if t in all_set]
        title_matched = [t for t in weights if t in title_set]
        band = 'high' if score >= 0.90 else 'medium' if score >= 0.70 else 'low'
        item = dict(article)
        item.update({
            'relevance_score': score,
            'relevance_band': band,
            'relevance_method': 'local_weighted_lexical_v1_no_llm',
            'relevance_terms': matched[:30],
            'relevance_title_terms': title_matched[:30],
            'relevance_explanation': (
                f"Matched {len(matched)}/{len(weights)} query terms; "
                f"{len(title_matched)} appear in the title. Ranking aid only; "
                "check meaning and eligibility during human screening."
            ),
        })
        scored.append(item)
    return sorted(scored, key=lambda x: x.get('relevance_score', 0), reverse=True)
