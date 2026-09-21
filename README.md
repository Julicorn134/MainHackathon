# TrialMatch

An evidence-backed clinical-trial screening prototype: paste a synthetic patient profile, retrieve recruiting studies from ClinicalTrials.gov, and review potential matches, missing information, and apparent mismatches with source evidence.

## Project status

Planning baseline for a four-person, four-hour hackathon. Application implementation has not started. The shared interfaces and work ownership are defined so all four people can start in parallel.

- [Four-person work plan](docs/TEAM_PLAN.md)
- [Shared interfaces and data contracts](docs/CONTRACTS.md)

## MVP workflow

1. Paste or load a synthetic patient profile.
2. Extract facts, dates, units, and evidence; let the user correct them.
3. Search recruiting interventional studies by condition.
4. Screen a bounded candidate set against the full registry eligibility text and structured eligibility fields.
5. Display ranked results with criterion-level evidence and focused follow-up questions.

Use three screening outcomes: **Potential match**, **Needs information**, and **Apparent mismatch**. Technical failures are **Not assessed**. Study teams determine enrollment eligibility; this prototype supports preliminary screening.

## Initial scope

- One condition: type 2 diabetes.
- Three synthetic demo profiles.
- Retrieve up to 50 candidates; assess up to 10 initially.
- Show search limits, record timestamps, site status, and links to source records.
- Flag complex cohort logic or ambiguous requirements for manual review.

## Proposed stack

Python, Streamlit, an HTTP client, Pydantic for shared schemas, and an existing LLM endpoint with structured output. Keep provider credentials on the server. The team should choose the LLM provider and model at kickoff and pin compatible dependencies during implementation.

The four-hour target assumes the team knows the stack and already has working LLM access. No training, database, user accounts, or EHR integration is required for this scope.

## Data and references

- [ClinicalTrials.gov v2 API](https://clinicaltrials.gov/data-api/api): public trial records, no API key needed. Detailed eligibility is primarily narrative text.
- [ClinicalTrials.gov dataset timestamp](https://clinicaltrials.gov/api/v2/version): check freshness separately from an individual record's last update.
- [Synthea downloads](https://synthetichealth.github.io/downloads.html): ready-made synthetic patient records; use small samples for fixtures.
- [TrialGPT criterion annotations](https://huggingface.co/datasets/ncbi/TrialGPT-Criterion-Annotations): useful evaluation material; review label conventions for missing information before reuse.
- [TrialGPT paper](https://www.nature.com/articles/s41467-024-53081-z) and [TrialMatchAI paper](https://www.nature.com/articles/s41467-026-70509-w): related work. Our hackathon emphasis is the review workflow and evidence traceability.

Use synthetic patient information for this demo. Missing history is unknown, not evidence of absence. Real patient use requires a separately designed and reviewed deployment.

## Team workflow

Each person owns a feature branch and separate files. Person 4 coordinates integration and reviews changes to shared contracts. Agree on contract changes before implementing them, keep pull requests small, and integrate the first working path by the end of hour two.

The proposed application layout and branch names are listed in the work plan; those modules are not implemented yet.
