# V5 changes from V4

1. Added `agents/relevance_agent.py`: corpus-relative TF-IDF cosine relevance scoring, with score, band, method, and matching-term explanation.
2. Added a `relevance_scoring` node to the LangGraph workflow between metadata quality and preliminary screening.
3. Retrieval now supports multiple distinct OpenAlex query formulations when both topic and research question are provided, merges duplicates, and respects the requested result limit.
4. Exports include relevance scores and the PRISMA statistics include high/medium/low relevance counts.
5. No LLM provider or paid API key is required. This is a local explainable ranking step, not an LLM agent.

Human review remains mandatory.

## V5.3 – improved generic relevance ranking
- Replaced corpus-relative TF-IDF cosine with explainable weighted lexical coverage.
- Gives topic terms priority over research-question and inclusion-criteria terms.
- Weights title matches more strongly than abstract-only matches and adds a small exact phrase bonus.
- Exports matched query terms, title-matched terms, and a plain-language explanation for every record.
- Uses conservative relevance bands (high >= 0.90; medium >= 0.70; low < 0.70).
- Updated the screening-method metadata label to V5.3 and the PRISMA statistics method label.
- Scores remain ranking aids only; no paper is automatically excluded because of a low relevance score. Human screening is still required.
