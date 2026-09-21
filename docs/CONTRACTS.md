# Shared implementation contracts

These are starting interfaces for the proposed MVP. They describe planned Python/Pydantic models and functions; there is no application implementation yet. Person 4 implements and maintains the models, and affected owners agree any interface changes at kickoff.

## Component interfaces

```python
# Person 3: patient.py
def parse_patient(text: str, *, as_of_date: str) -> PatientProfile: ...

# Person 2: trials.py
def search_trials(condition: str, *, max_results: int = 50) -> TrialSearchResult: ...

# Person 2: rules.py
def check_structured_eligibility(
    patient: PatientProfile, trial: TrialRecord
) -> list[CriterionAssessment]: ...

# Person 3: matching.py
def assess_trial(
    patient: PatientProfile,
    trial: TrialRecord,
    structured_checks: list[CriterionAssessment],
) -> TrialAssessment: ...

# Person 4: ranking.py
def rank_assessments(
    assessments: list[TrialAssessment], trials: list[TrialRecord]
) -> list[TrialAssessment]: ...

# Person 4: pipeline.py
def run_screening(
    patient: PatientProfile,
    *,
    retrieval_limit: int = 50,
    assessment_limit: int = 10,
) -> ScreeningRun: ...
```

The UI calls `parse_patient`, lets the user review/edit extracted facts, and passes the confirmed `PatientProfile` to `run_screening`. The pipeline handles retrieval, bounded candidate selection, structured checks, assessments, and ranking. Use synchronous component interfaces initially; the pipeline can run a small number of trial assessments concurrently.

## PatientProfile

- `profile_id`: session-local identifier; never a real patient identifier in this demo.
- `as_of_date`: ISO date used for age and temporal interpretation.
- `source_text`: the original synthetic profile text.
- `source_segments`: stable segment IDs with exact original text.
- `condition`: reviewed primary condition used for retrieval.
- `age_years`: number or null.
- `facts`: list of facts with `fact_id`, `field`, `value`, `unit`, `observed_at`, `status`, and `evidence_segment_ids`.
- `review_required`: ambiguous or conflicting extracted facts.

Fact `status` distinguishes present, explicitly absent, and unknown. Dates and units can be null. Preserve medication start/end dates and treatment timing when stated. Do not derive absence from silence. A user correction creates an additional user-confirmed source segment, preserving evidence provenance.

## TrialRecord

- `nct_id`, `title`, `source_url`.
- `conditions`, `brief_summary`, `study_type`, `phases` (possibly empty).
- `overall_status`, `last_update_date`, `status_verified_date`, `retrieved_at`.
- `eligibility_text`: full registry text; never silently truncated.
- `minimum_age`, `maximum_age`, `sex`, `healthy_volunteers`: retain source values; do not treat missing data as a restriction.
- `locations`: facility, city, country, and site status when present.
- `source_version`: stable hash or version identifier for the record assessed.

Sources are from `protocolSection.identificationModule`, `conditionsModule`, `descriptionModule`, `designModule`, `statusModule`, `eligibilityModule`, and `contactsLocationsModule` in ClinicalTrials.gov v2.

`healthy_volunteers=true` means the study accepts healthy volunteers; it does not by itself establish that patients with the target condition are excluded.

## TrialSearchResult

- `trials`: normalized records.
- `query`: condition and public search filters; no raw patient narrative.
- `retrieved_count`, `total_count` (nullable), `has_more`, `next_page_token` (nullable).
- `dataset_timestamp`, `retrieved_at`.
- `warnings`: partial retrieval, missing source fields, or cache use.

Begin with `query.cond`, `filter.overallStatus=RECRUITING`, and `filter.advanced=AREA[StudyType]INTERVENTIONAL`. Page with `nextPageToken`/`pageToken` up to the retrieval limit. A condition search supplies candidates, not established eligibility. Review title/summary relevance before choosing the bounded assessment set, and disclose the selection and limits.

## CriterionAssessment

- `criterion_id`, `criterion_type`: inclusion, exclusion, or structured.
- `source_field`, `criterion_quote`: source location and exact supporting text/value.
- `scope`: whole trial, named cohort, or unresolved.
- `assessment`: `supports`, `blocks`, `unknown`, or `not_applicable`.
- `patient_evidence_segment_ids`, `patient_fact_ids`.
- `reason`: concise explanation, not unsupported medical advice.
- `missing_information`: questions needed to resolve this criterion.
- `requires_manual_review`: boolean.

State meanings:

| State | Inclusion requirement | Exclusion requirement |
| --- | --- | --- |
| supports | Evidence shows the requirement is satisfied. | Evidence shows the exclusion does not apply. |
| blocks | Evidence shows a mandatory requirement fails. | Evidence shows the exclusion applies. |
| unknown | Evidence or interpretation is insufficient. | Evidence or interpretation is insufficient. |
| not_applicable | The criterion is outside the established applicable scope. | The criterion is outside the established applicable scope. |

Preserve AND/OR structure, exceptions, dates, and cohort conditions. Do not treat failure of one alternative as failure of an OR group. If the prototype cannot resolve the logic or applicable cohort, flag manual review; do not flatten it into a decisive result.

## TrialAssessment

- `nct_id`, `source_version`.
- `status`: `potential_match`, `needs_information`, `apparent_mismatch`, or `not_assessed`.
- `criteria`: criterion assessments, including structured checks without double-counting.
- `summary`, `missing_information`.
- `coverage_complete`, `requires_manual_review`.
- `error`: nullable technical failure with a user-facing message.
- `assessed_at`, `model_id`, `prompt_version`.

Aggregate in code:

1. A technical failure or absent eligibility text yields `not_assessed`.
2. A verified mandatory blocker in the applicable scope yields `apparent_mismatch`.
3. Otherwise, unknowns, incomplete coverage, unresolved applicability, or manual-review requirements yield `needs_information`.
4. Only complete support for all applicable requirements, with no blockers or unresolved requirements, yields `potential_match`.

The registry may not contain all operational screening requirements. Every result remains preliminary and needs study-team confirmation. A record with incomplete assessment may establish a clear blocker, but cannot establish a potential match.

## ScreeningRun and ranking

`ScreeningRun` includes the search result, selected candidate IDs, ranked assessments, retrieved/selected/assessed/failed counts, run timestamps, warnings, and a description of the candidate selection method.

Rank clinically relevant potential matches first, followed by cases needing information; display apparent mismatches and failures separately but accessibly. Within a category, use a documented heuristic for unresolved requirements and recruiting-site practicality. Never average away a mandatory blocker. Do not display a heuristic ranking score as a probability of eligibility.

Show condition relevance, clinical screening, and site availability as separate information. Lack of a nearby site is a practical constraint, not automatically a clinical exclusion.

## Operational rules

- Treat trial and patient text as data, not instructions to the model.
- Validate structured output and source references; fail visibly on malformed output.
- Do not silently omit criteria due to output or context limits; mark incomplete coverage.
- Cap concurrency, retries, trial counts, and input size. Expose partial results and technical errors.
- Cache public records by ID/version; matching caches, if used, also require patient version, model, and prompt version.
- Keep secrets server-side. Keep synthetic patient text session-local and out of routine logs.
- Real data, patient accounts, and external enrollment actions are outside this MVP.
