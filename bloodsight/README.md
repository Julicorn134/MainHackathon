# BloodSight AI prototype

Python/Streamlit application using synthetic data. Work from the repository's `bloodsight` branch. The [source brief](../docs/source/BloodSight-original.pdf), [requirements](../docs/BLOODSIGHT_REQUIREMENTS.md), [team plan](../docs/BLOODSIGHT_TEAM_PLAN.md), and [contracts](../docs/BLOODSIGHT_CONTRACTS.md) define the current build.

## Run

Run from this directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

The store creates an ignored `state.json`. Set `BLOODSIGHT_STATE` to a disposable JSON path before starting the app or tests to isolate a demonstration. Use a new path for a fresh seed. `python forecast.py 2026-09-21` regenerates tracked `data.csv`; this changes fixture and forecast values.

## Demo accounts

| Username | Password | Role |
| --- | --- | --- |
| centre | centre123 | Blood centre: outlook, requests, bookings, notifications |
| lab | lab123 | Laboratory: reports and patient notifications |
| patient | patient123 | Alex, O-, donor preferences enabled |
| patient2 | patient123 | Sam, A+, donor preferences disabled |

These are public credentials for synthetic accounts. `login.py` handles the interface and `store.py` implements account/state operations. Lab is a separate role from centre. The donor view now has Results, Needs, Donations, a rule-based Ask screen, Notifications and Me; it still needs booking-capacity/error handling, contact details and verification against the shared data changes.

## Files

| File | Responsibility |
| --- | --- |
| `app.py` | Role-based entry point |
| `login.py`, `ui.py` | Login and shared presentation |
| `store.py` | JSON state, fixtures, matching, requests, bookings, notifications, lab reports |
| `forecast.py`, `data.csv` | Synthetic history, ridge regressions, projections and scenarios |
| `views/outlook.py` | Forecast dashboard and campaign prefill |
| `views/centre.py` | Staff requests and bookings |
| `views/lab.py` | Existing lab workflow |
| `views/patient.py` | Existing donor/results portal to extend and verify |
| `tests/ACCEPTANCE.md` | Earlier manual checklist; not a test result |

## Existing forecast

The generator produces 180 days for eight blood types. Separate ridge regressions predict demand and donations over 14 days using recent history, weekday, trend and configured holidays. Inventory is projected from opening stock plus supply minus demand. Safety/warning thresholds use three/five days of average demand; these are demo assumptions. The plotted band is heuristic, not a calibrated clinical confidence interval.

The existing backtest is a single synthetic holdout and is not real-world validation. Derive quantities and dates from the fixture; the old fixed 210-donation example is not an acceptance requirement.

## Intended integrated demonstration

Staff inspect a forecast and dated stock report, create a targeted request and view aggregate responses. An opted-in synthetic donor sees the request, books an available appointment and can cancel it. Staff see the booking and dated expected supply. Campaign closure must preserve appointments. Manual audits, facility demand and expiry are new work in the build prompts.

Distinguish bookings, expected donations and usable inventory. Notifications remain inside the demonstration. Preserve existing laboratory features; the PDF's blood-supply workflow takes priority over expanding them.
