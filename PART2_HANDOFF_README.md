# Part 1 → Part 2 handoff

## Main input
Use `outputs/<topic_slug>/part2_handoff.json` as the main input file. It contains records not automatically excluded by the preliminary title/abstract and publication-type rules. It includes both `potentially_include` and `uncertain` records; do not treat either decision as final eligibility.

## Supporting files
- `human_review.xlsx`: researcher can fill `Human decision (fill in)` with `Include`, `Exclude`, or `Unclear`, and add reviewer notes.
- `full_texts/`: PDFs successfully downloaded from OpenAlex open-access URLs.
- `pdf_acquisition_results.json`: per-record PDF acquisition status and local PDF path where available.
- `research_protocol.json`: topic, question, criteria, and publication-type policy.
- `prisma_statistics.json`: preliminary acquisition and screening counts.

## Important record fields
- `openalex_id`, `doi`, `title`, `year`, `authors`, `abstract`, `type`
- `landing_page_url`, `pdf_url`, `is_oa`
- `title_abstract_decision`, `title_abstract_reason`
- `screening_inclusion_hits`, `screening_exclusion_hits`
- `metadata_completeness`, `missing_metadata`
- `human_review_required`, `screening_is_final`

## Expected Part 2 tasks
1. Full-text retrieval where a PDF is not already available, respecting access rights.
2. Human full-text eligibility screening against the validated protocol.
3. Data extraction and quality/risk-of-bias assessment.
4. Evidence/RAG synthesis and narrative synthesis.
5. Final PRISMA flow counts reconciled with actual human decisions.

**Do not use Part 1 automated preliminary decisions as final PRISMA inclusion/exclusion decisions.**
