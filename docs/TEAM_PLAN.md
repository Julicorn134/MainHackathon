> Historical TrialMatch planning document. For the current BloodSight project, use [the requirements](BLOODSIGHT_REQUIREMENTS.md), [team plan](BLOODSIGHT_TEAM_PLAN.md), and [contracts](BLOODSIGHT_CONTRACTS.md).

# TrialMatch: four-person work plan

This plan divides implementation among four human contributors. Replace Person 1-4 with team members' names at kickoff. Each owns a separate branch and file area; Person 4 coordinates integration, while each owner fixes defects in their own component.

## Ownership

| Owner | Branch | Responsibility | Owned files to create | Completion criteria |
| --- | --- | --- | --- | --- |
| Person 1: UI and demo experience | `feat/ui` | Streamlit input, editable extracted facts, ranked result cards, evidence details, follow-up inputs, and progress/error states | `app.py`, `ui/` | A user can load a fixture, confirm facts, search, inspect evidence, answer a missing-information question, and rerun. |
| Person 2: trial retrieval and deterministic checks | `feat/trial-data` | ClinicalTrials.gov client, pagination, normalization, public-data cache, structured age checks, and supported numeric comparisons | `trialmatch/trials.py`, `trialmatch/rules.py`, `tests/test_trials.py`, `tests/test_rules.py` | Live recruiting trials arrive in the shared schema with full eligibility, source URLs, dates, site statuses, and honest search limits. |
| Person 3: patient extraction and matching | `feat/matching` | LLM adapter, patient fact extraction, criterion-level interpretation, evidence references, unknown handling, and trial-level aggregation | `trialmatch/patient.py`, `trialmatch/matching.py`, `trialmatch/llm.py`, `prompts/`, `tests/test_matching.py` | Each assessed criterion has an interpretable state and evidence; missing data and unsupported logic cannot become an eligible result. |
| Person 4: contracts, integration, and evaluation | `feat/integration` | Shared models, fixtures, orchestration, ranking, dependency setup, cross-component tests, and release/demo coordination | `trialmatch/models.py`, `trialmatch/pipeline.py`, `trialmatch/ranking.py`, `trialmatch/__init__.py`, `fixtures/`, `tests/test_pipeline.py`, `tests/test_ranking.py`, dependency files, project documentation | End-to-end flow works, fixtures exercise the three outcomes, limits/errors are visible, and fresh setup instructions are verified. |

Person 4 also owns `.gitignore`, `.env.example`, and dependency-lock changes. Do not commit credentials or real patient information.

## First 15 minutes: agree once, then work independently

1. Confirm Python version, LLM provider/model, and access to the provider.
2. Read [CONTRACTS.md](CONTRACTS.md) together. Person 4 creates the shared Pydantic models and minimal synthetic fixtures first.
3. Keep the initial demo condition as type 2 diabetes and initial assessment limit at 10 trials.
4. Person 1 starts with mocked results. Person 2 uses the public API. Person 3 starts with a fixture patient and saved criteria. None needs to wait for a complete end-to-end backend.
5. Person 4 publishes the first shared-model commit for the other branches to pull before integration.

## Four-hour schedule

| Time | Person 1 | Person 2 | Person 3 | Person 4 |
| --- | --- | --- | --- | --- |
| 0:00-0:15 | Agree contracts and sketch screen | Agree contracts and validate API access | Agree contracts and validate LLM access | Lead kickoff; create models and minimal fixtures |
| 0:15-1:00 | Build input and results against fixtures | Implement search and normalization | Implement patient extraction and one-trial assessment | Set up dependencies, fixture labels, and pipeline skeleton |
| 1:00-2:00 | Add editable facts and evidence panels | Add pagination, freshness, site status, and basic checks | Add evidence validation, unknowns, and aggregation | Integrate components; implement ranking and bounded orchestration |
| 2:00-3:00 | Connect live results and follow-up inputs | Test live API edge cases and caching | Test missing facts, explicit negatives, and criterion logic | Run end-to-end cases; coordinate fixes and dependency documentation |
| 3:00-3:30 | Polish the complete user journey | Resolve retrieval failures and verify source links | Resolve incorrect assessments in held-out fixtures | Freeze features; verify setup and collect evaluation results |
| 3:30-4:00 | Lead demo walkthrough | Verify fresh trial records and fallback snapshots | Explain evidence and uncertainty during rehearsal | Rehearse full demo; merge ready changes and record known limits |

Integration checkpoints: shared models by minute 15; all components work independently by minute 60; first live end-to-end result by minute 120; feature freeze by minute 210.

## Acceptance checks

- A missing medication history produces unknown, while an explicit negative history can support a criterion when its scope and timing fit.
- A mandatory blocker cannot be offset by several supported criteria.
- Inclusion and exclusion rules have opposite effects on eligibility and are aggregated correctly.
- Age boundaries, units, collection dates, and treatment timing are handled explicitly; unsupported comparisons remain unknown.
- AND/OR alternatives, exceptions, and cohort-specific rules are preserved. Unresolved logic forces review.
- Every claimed source excerpt exists in the supplied patient or trial record. Quotes establish provenance, not proof of correct clinical interpretation.
- Overall study recruitment and individual site recruitment are displayed separately when they differ.
- Missing eligibility, an API error, a timeout, or invalid model output is not reported as a patient mismatch.
- Cached demo results are labeled as cached and show their retrieval date.
- The UI states how many trials were retrieved and assessed and whether more results exist.

Person 4 creates a small manually reviewed evaluation set with cases held out from prompt tuning. Report false matches, false exclusions, and unknown handling separately; this is prototype evaluation, not clinical validation.

## Scope boundaries

Implement one condition, three synthetic profiles, a bounded live search, and evidence-backed results. Defer accounts, patient persistence, EHR/FHIR ingestion, maps, a vector database, broad disease coverage, fine-tuning, and autonomous enrollment. Downloaded Synthea records can be simplified into checked demo profiles; building a general FHIR importer is outside the four-hour scope.

## Git workflow

After cloning, each contributor creates their assigned branch from `main`:

```bash
git switch main
git pull --ff-only
git switch -c feat/ui
```

Replace `feat/ui` with the branch from the ownership table. Open small pull requests into `main`. Person 4 coordinates merge order; contributors review relevant changes. Changes to the shared contract must be agreed with affected owners before merging.

## Demo story

Use clearly labeled synthetic profiles to show a potential match, a documented exclusion, and an unresolved criterion that becomes assessable after adding one fact. Open the original criterion for each explanation. Keep any curated demonstration separate from held-out evaluation results.
