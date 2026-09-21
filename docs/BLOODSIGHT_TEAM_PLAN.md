# BloodSight: four people, one integrated build

Start from the latest `origin/bloodsight`, not `main`. Use separate clones/worktrees and feature branches. These are complete assignments for each person to paste into their coding assistant or use as a build brief.

| Person | Ownership | Branch | Prompt |
| --- | --- | --- | --- |
| 1 | Forecast, synthetic history, forecast view | `feat/bloodsight-forecast` | [1: Forecast](prompts/01_FORECAST.md) |
| 2 | Store, inventory, matching, appointments, data contracts | `feat/bloodsight-data` | [2: Data and bookings](prompts/02_DATA_AND_BOOKINGS.md) |
| 3 | Staff/common UI, integration and demo | `feat/bloodsight-staff` | [3: Staff and integration](prompts/03_STAFF_AND_INTEGRATION.md) |
| 4 | Donor portal and its helpers | `feat/bloodsight-donor` | [4: Donor portal](prompts/04_DONOR_PORTAL.md) |

## File boundaries

| Person | Files they may change without coordination |
| --- | --- |
| 1 | `bloodsight/forecast.py`, `bloodsight/data.csv`, `bloodsight/views/outlook.py`, new `bloodsight/forecast_*.py`, `bloodsight/tests/test_forecast*.py` |
| 2 | `bloodsight/store.py`, new `bloodsight/inventory.py` / `bloodsight/fixtures/`, `bloodsight/tests/test_store*.py`, `bloodsight/tests/test_inventory*.py`, `docs/BLOODSIGHT_CONTRACTS.md` |
| 3 | `bloodsight/app.py`, `bloodsight/login.py`, `bloodsight/ui.py`, `bloodsight/views/centre.py`, `bloodsight/views/lab.py`, `bloodsight/.streamlit/`, `bloodsight/requirements.txt`, README files, manual acceptance/demo docs, new integration tests |
| 4 | `bloodsight/views/patient.py`, new `bloodsight/views/donor_*.py`, `bloodsight/tests/test_donor*.py` |

Request cross-owner changes with a concrete signature or small patch proposal. Do not copy the store or replace another person's file to fix a dependency. Person 2 maintains the contract; Person 3 integrates reviewed branches into `bloodsight` in small steps. Contributors commit to their own branches and hand over a diff and results. Keep `main` untouched unless the team decides to promote the completed prototype.

## Four-hour sequence

| Time | Everyone | Person 1 | Person 2 | Person 3 | Person 4 |
| --- | --- | --- | --- | --- | --- |
| 0:00–0:20 | Read brief/contracts; run app | Confirm fixture and site IDs | Publish interfaces and seed schema | Confirm routing/integration checkout | Map screens to store methods |
| 0:20–1:30 | Build P0 slice | Site forecast, dated supply, presets | Lots/audits, matching/booking guards | Inventory/network UI, request handoff | Needs, booking/cancel, inbox |
| 1:30–2:00 | Integrate first full loop | Connect store output | Resolve contract mismatches | Combine branches; test staff → donor → staff | Verify shared state, not UI-only success |
| 2:00–3:10 | Close P0 gaps | Explanations, backtest, expiry | Repeated actions, closed campaigns, limits | Freshness, clarity, role boundaries | History, preferences, contact, empty states |
| 3:10–4:00 | Freeze and rehearse | Forecast fixes | State fixes | Record checks and lead demo | Verify donor flow in second session |

P1 starts only after integrated acceptance passes. Weather/outbreak feeds, broader seasonality, rewards and advanced lab interactions must not displace the core loop. Four hours is a target for this narrow continuation of the existing prototype, not the full PDF vision.

## Integration decisions

- Keep existing `centre`, `lab`, `patient` roles and demo credentials.
- Resolve the centre from `user['org']`. A regional table may show all sites; forecast selection does not grant another facility's campaign editing rights.
- Preserve the existing `views.outlook.render(user)` interface. Person 1 adds facility to request prefill; Person 3 consumes it before constructing navigation, avoiding the current exception-based handoff.
- Preserve existing store APIs. Publish new interfaces before consumers need them. Tests can use contract-shaped fixtures; final app code uses the shared implementation.
- Use temporary `BLOODSIGHT_STATE` and fixed dates in tests. Do not modify a teammate's state.
- Reconcile seeded current stock with the same per-facility history used by forecasts.

## Completion

Demonstrate a shortage, its explanation and freshness, a prefilled request, a donor booking in another session, dated expected supply, and a +100 scenario. Show pause/opt-out or a full slot, and that closing a campaign retains appointments.

Each person reports changed files, checks actually run, a screen walkthrough and gaps. Person 3 updates the README and acceptance log to final behaviour and records deferred P1 items. A written checklist is not a passing test run.
