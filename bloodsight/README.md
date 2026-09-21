# BloodSight AI prototype

Python/Streamlit application using synthetic data. Work from the repository's `bloodsight` branch. The [source brief](../docs/source/BloodSight-original.pdf), [requirements](../docs/BLOODSIGHT_REQUIREMENTS.md), [team plan](../docs/BLOODSIGHT_TEAM_PLAN.md), and [contracts](../docs/BLOODSIGHT_CONTRACTS.md) define the current build.

## Run

Use Python 3.11 or newer. Run from this directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

The existing demo account/booking store creates an ignored `state.json`. Uploaded records can be shared in **Supabase**: copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and fill in `SUPABASE_SECRET_KEY`. The project URL is included. See [the database setup and tables](../supabase/README.md). Cloud failures are reported without substituting local records.

For offline tests, explicitly set `BLOODSIGHT_DATA_BACKEND = "sqlite"`; records then persist in `state.sqlite3`. Set `BLOODSIGHT_STATE` and optionally `BLOODSIGHT_DB` before starting to isolate a demonstration. Keep a persistent disk for the demo account/booking state even when uploaded data uses Supabase. `python forecast.py 2026-09-21` only regenerates the bundled synthetic CSV; it does not replace database records.

## Deposit data and use AI

1. Log in as **centre**, open **Data**, and upload the downloadable history CSV or enter daily figures. Preview validates the full file before saving. Corrections replace the same date/type; unchanged repeats do not duplicate rows.
2. Open **Outlook → Uploaded data**. Forecasts fit the saved records; each blood type needs 42 consecutive daily rows. Incomplete history is shown explicitly. The bundled demo requires an explicit selection.
3. Log in as **lab**, open **Data**, and upload the JSON report template or enter a measured value. Review drafts and publish them. Urgent reports require a recorded phone call. Once published, imported reports replace the matching patient's bundled lab-history view; they are not mixed with invented measurements.
4. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml`, choose `AI_PROVIDER = "openrouter"`, and set `OPENROUTER_API_KEY`. The default model is `openai/gpt-4.1-mini`; change `OPENROUTER_MODEL` for another compatible model. Direct OpenAI remains available with `AI_PROVIDER = "openai"` and `OPENAI_API_KEY`. This local file is ignored by Git; environment variables override these settings. Do not paste keys into source files.
5. Use **centre → AI assistant**, **patient → Ask**, or **Results → Open value → Explain this recorded value**. Each request calls the selected AI service with the relevant allowed records and displays its source evidence and provider. No key or an API failure produces a clear message, never a template answer.

Only test data belongs in this demo. [Full setup, limits and verification](../docs/DATA_AND_AI.md). [Recommended future integrations](../docs/BLOODSIGHT_INTEGRATIONS.md).

## Demo accounts

| Username | Password | Role |
| --- | --- | --- |
| centre | centre123 | Blood centre: outlook, requests, bookings, notifications |
| lab | lab123 | Laboratory: reports and patient notifications |
| patient | patient123 | Alex, O-, donor preferences enabled |
| patient2 | patient123 | Sam, A+, donor preferences disabled |

These are public credentials for synthetic accounts, not production identity management. `login.py` handles the interface and `store.py` handles existing account/state operations. Lab is a separate role from centre. Patient Ask and value explanations now use the API. The older donor matching/booking simulation still needs the safeguards identified in the team plan.

## Files

| File | Responsibility |
| --- | --- |
| `app.py` | Role-based entry point |
| `login.py`, `ui.py` | Login and shared presentation |
| `store.py` | JSON state, fixtures, matching, requests, bookings, notifications, lab reports |
| `data_store.py`, `views/data.py` | Validated imports, manual entry, reports and publication |
| `supabase_store.py`, `storage_config.py`, `../supabase/` | Cloud storage adapter, server settings, applied schema and SQL checks |
| `ai_service.py`, `ai_config.py`, `views/ai_panel.py` | Role-scoped evidence, real AI requests, local credentials, source display |
| `forecast_data.py` | Explicit source selection and daily-history quality checks |
| `forecast.py`, `data.csv` | Synthetic history, ridge regressions, projections and scenarios |
| `views/outlook.py` | Forecast dashboard and campaign prefill |
| `views/centre.py` | Staff requests and bookings |
| `views/lab.py` | Existing lab workflow |
| `views/patient.py` | Existing donor/results portal to extend and verify |
| `tests/ACCEPTANCE.md` | Earlier manual checklist; not a test result |

## Existing forecast

The bundled generator produces 180 days for eight blood types. Separate ridge regressions predict demand/donations over 14 days using recent history, weekday, trend and observed holiday flags. Uploaded history is scoped to the centre organisation; no future holiday calendar is assumed for those records. Inventory uses closing stock plus predicted supply minus demand. Safety/warning thresholds use three/five days of average demand: demo assumptions. The plotted band is heuristic, not a calibrated clinical confidence interval.

The backtest holds out the last 14 days of the selected dataset. This is not real-world validation; errors on synthetic data are synthetic results. The old fixed 210-donation example is not an acceptance requirement.

## Intended integrated demonstration

Staff inspect a forecast and dated stock report, create a targeted request and view aggregate responses. An opted-in synthetic donor sees the request, books an available appointment and can cancel it. Staff see the booking and dated expected supply. Campaign closure must preserve appointments. Manual audits, facility demand and expiry are new work in the build prompts.

Distinguish bookings, expected donations and usable inventory. Notifications remain inside the demonstration. Preserve existing laboratory features; the PDF's blood-supply workflow takes priority over expanding them.
