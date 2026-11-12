# Project submission checklist

Aligned with *Project Agentic AI Pipeline* requirements.

## Source code

- [ ] All source code pushed to GitHub or GitLab
- [ ] `.env` secrets are **not** committed (use `.env.example` only)
- [ ] Part 1 entry point: `main.py`
- [ ] Part 2 entry point: `main_part2.py`

## Documentation

- [ ] Root [README.md](README.md) — documentation unique (Partie 1 + Partie 2 + handoff)
- [ ] Individual contributions described in the final team report (max 5 members)

## Demonstration

- [ ] End-to-end demo on one real topic **or** offline fixture:

```powershell
python tools/create_part2_demo_fixture.py
python main_part2.py --output-dir outputs/demo_cybersecurity_in_iot
```

- [ ] Video demonstration ≤ 3 minutes covering:
  - [ ] Topic intake / Part 1 run (or fixture explanation)
  - [ ] Human review step
  - [ ] Part 2 artefacts (evidence table, synthesis, PRISMA, critic)
- [ ] Show `outputs/<topic>/part2/evaluation.json` metrics briefly

## Evaluation evidence to capture for the report

From `part2/evaluation.json` and `part2/critic_report.json`:

- Completeness: screened / included / extracted / appraised
- Transparency: rationale rate, human final decisions
- Consistency: critic verdict + issues
- Time savings: compare pipeline wall-clock vs estimated manual screening/extraction for the demo corpus

## PRISMA / methodological soundness

- [ ] Protocol validated by the team before claiming final results
- [ ] Human Include/Exclude filled where required
- [ ] `prisma_reconciled.json` used for final flow counts (not Part 1 preliminary excludes alone)
- [ ] Manuscript draft reviewed manually (`review_manuscript_draft.md`)
