# Part 1 — Research & Literature Acquisition Pipeline 

A topic-agnostic pipeline orchestrated with LangGraph. It drafts a protocol and search strategy, retrieves scholarly metadata from OpenAlex, deduplicates records, checks metadata quality, calculates explainable local TF-IDF relevance scores, performs preliminary title/abstract and publication-type screening, optionally downloads open-access PDFs, and exports a handoff for Part 2.

## Important about AI / API keys

- **No LLM API key is required.** OpenAlex is used for scholarly metadata retrieval.
- Relevance ranking uses local TF-IDF cosine similarity (Python only), not a generative LLM or a trained semantic model.
- Scores help prioritize records; they do **not** make final include/exclude decisions. Human screening is still required.
- OpenAlex is the only scholarly database connected in this version.

## 1. Setup (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Run

```powershell
python main.py --topic "Cybersecurity in IoT" --question "What security threats and mitigation techniques are studied for IoT systems?" --max-results 50
```

Optional inclusion/exclusion terms and PDF acquisition:

```powershell
python main.py --topic "Deep Learning for Medical Diagnosis" --max-results 100 --include "deep learning" diagnosis medical --exclude editorial --download-pdfs
```

You can replace the topic and research question with any research subject. Do not use a topic-specific code change.

## 3. Publication-type policy

Default policy:
- Accepted for screening: research articles (`article`), review articles (`review`), conference/proceedings papers (`proceedings-article`), and book chapters (`book-chapter`).
- Excluded by default: letters (`letter`) and editorials (`editorial`).
- Other types are not automatically rejected unless an explicit `--include-types` allow-list is supplied.

Example allow-list:

```powershell
python main.py --topic "Your research topic" --include-types article review proceedings-article book-chapter
```

## 4. Outputs

Each run is saved under `outputs/<topic_slug>/`, including:
- `research_protocol.json` and `search_strategy.json`;
- `articles_raw.json`, `articles.json`, and `duplicates.json`;
- `screening_results.json` and `screening_results.csv`;
- `prisma_statistics.json` with preliminary counts and relevance-band counts;
- `human_review.xlsx` with reviewer decision dropdown and notes;
- `part2_handoff.json` and `part2_handoff.csv`;
- optional `pdf_acquisition_results.json` and `full_texts/`.

## 5. Handoff to Part 2

Share the complete output folder with the Part 2 teammate, especially `part2_handoff.json`, `human_review.xlsx`, `full_texts/` (if PDFs were acquired), `research_protocol.json`, and `prisma_statistics.json`.

## 6. Methodological limitations

- OpenAlex is the only scholarly metadata source connected in V5; results are not a comprehensive search of all scholarly databases.
- The search strategy and protocol are automatically drafted and must be validated by the research team.
- TF-IDF is lexical similarity, not deep semantic understanding. Synonyms and conceptual equivalence may be missed.
- Automated screening is preliminary. Never report automated decisions as final PRISMA eligibility decisions.
- PDFs are downloaded only from open-access URLs supplied by OpenAlex; paywalls and access controls are not bypassed.

