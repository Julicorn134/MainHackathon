# BloodSight AI

**Predict. Prepare. Prevent Shortages.**

A hackathon prototype for forecasting blood demand, reviewing inventory across facilities, and inviting opted-in synthetic donors to book appointments. The project uses test data; the intended setting is a service with limited resources and manually reported stock.

The active implementation is on the **`bloodsight` branch**, in [`bloodsight/`](bloodsight/). The earlier TrialMatch plan remains in Git history and two historical planning files; it is not the current build brief.

## Start here

1. [Original Google Docs PDF — source brief](docs/source/BloodSight-original.pdf)
2. [Requirements, current gaps and MVP priorities](docs/BLOODSIGHT_REQUIREMENTS.md)
3. [Four-person ownership and integration plan](docs/BLOODSIGHT_TEAM_PLAN.md)
4. [Shared implementation contracts](docs/BLOODSIGHT_CONTRACTS.md)
5. [Saving data and connecting the real AI](docs/DATA_AND_AI.md)
6. [Services and connectors for different blood banks](docs/BLOODSIGHT_INTEGRATIONS.md)
7. [Supabase tables, cloud import setup and verification](supabase/README.md)

Give each person their complete prompt:

| Person | Build area | Copy-ready prompt |
| --- | --- | --- |
| 1 | Forecasts, synthetic history and scenarios | [Prompt 1](docs/prompts/01_FORECAST.md) |
| 2 | Shared data, inventory, matching and bookings | [Prompt 2](docs/prompts/02_DATA_AND_BOOKINGS.md) |
| 3 | Staff dashboard and integration | [Prompt 3](docs/prompts/03_STAFF_AND_INTEGRATION.md) |
| 4 | Donor portal | [Prompt 4](docs/prompts/04_DONOR_PORTAL.md) |

## Run the existing prototype

From a clone of this repository:

```powershell
git switch bloodsight
git pull --ff-only origin bloodsight
cd bloodsight
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

Use separate clones or worktrees for parallel work. See [application notes and demo accounts](bloodsight/README.md).

## Current state

The data/AI implementation adds shared Supabase storage, CSV and manual history entry, draft/published lab-report imports, forecasts trained on saved facility records, and a real OpenAI assistant with source records. It replaces the patient's template answers. The prototype still uses local demo identities and booking state; expiry, regional stock and dated campaign supply remain separate work. See [setup and verified scope](docs/DATA_AND_AI.md).

The PDF records the full vision. The requirements separate that feature list from the narrower four-hour MVP. Live integrations, real outreach and deployment with a healthcare organisation are outside this synthetic demonstration.
