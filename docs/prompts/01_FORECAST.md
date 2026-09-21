# Person 1 — Forecasts, synthetic history and scenarios

Copy the assignment below into your coding assistant.

---

Implement the forecast workstream for **BloodSight AI** in https://github.com/Julicorn134/MainHackathon. Continue the existing Python/Streamlit prototype. Use the latest `origin/bloodsight` as your base, in your own clone/worktree, and create `feat/bloodsight-forecast`. Do not start from the old TrialMatch plan on main. Inspect local changes before switching branches and preserve teammates' work.

Read `docs/source/BloodSight-original.pdf`, `docs/BLOODSIGHT_REQUIREMENTS.md`, `docs/BLOODSIGHT_TEAM_PLAN.md`, and `docs/BLOODSIGHT_CONTRACTS.md`. The PDF is the product vision; the requirements document identifies the four-hour P0 scope. Implement and verify that scope rather than only returning a plan. All data must be synthetic. No live API, LLM, credentials or healthcare partner is required.

You own `bloodsight/forecast.py`, `bloodsight/data.csv`, `bloodsight/views/outlook.py`, new `bloodsight/forecast_*.py` helpers and `bloodsight/tests/test_forecast*.py`. Person 2 owns the store and shared contracts; Person 3 owns the staff/common UI and dependencies; Person 4 owns the donor portal. Request cross-owner changes rather than editing their files.

The existing code has ridge demand/donation forecasts, a 14-day horizon, risk thresholds, a campaign recommendation, a what-if overlay and one synthetic holdout. History is aggregated, the outlook hardcodes `rbc`, booking supply is applied through a fixed window, and clipped inventory can conceal unmet demand. Inspect these paths before extending them.

Build these P0 outcomes in order:

1. Create reproducible synthetic history for `rbc`, `mumc`, `heerlen` and all eight existing blood types. Add `place_id` while retaining existing columns and stable seed/date. Include one shortage and one adequate-stock case; do not duplicate the old aggregate at each site. Share latest closing stocks with Person 2 so inventory lots reconcile. Read legacy data as `rbc` only.
2. Add the contract's `forecast_for_place(...)` wrapper and retain existing positional APIs. Filter the history to one facility before fitting. Support audited starting stock, lot expiry and dated incremental campaign appointments. Use an explicit first-expiring-first-out assumption and track unmet demand; do not subtract a consumed lot again at expiry. A cancelled booking contributes nothing, and a closed campaign's active appointment still contributes once on its usable date.
3. Preserve the existing `render(user)` interface and add facility/type selection, data/audit date, stale-data status, 14-day chart, risk and understandable drivers. Coordinate the staged request navigation with Person 3; do not assign the `nav` widget state after its creation. Show routine supply, booked supply and what-if additions distinctly. Do not retain the old total-bookings overlay on top of dated supply.
4. Add explicit +50/+100/+200 donation presets with timing controls and explain their yield/processing-delay assumptions. Preserve the useful current slider. Scenarios must not mutate stock or bookings. Recommendations must be recalculated from the selected facility, current inputs and actual forecast; never hardcode 180 or 210 units.
5. Preserve the `request_prefill` handoff and add `place_id` as specified in the contract. A regional viewer cannot create another organisation's request merely by selecting its forecast. Explain synthetic assumptions, heuristic uncertainty bands and the fact that donor invitations are not medical clearance.
6. Compare the model with a simple recent-average baseline on chronological synthetic holdouts. Report an appropriate error and handle zero-demand series. Do not call synthetic evaluation real-world accuracy or imply 180 days validates annual seasonality.

Only after P0 works, add labelled simulated demand/turnout scenarios for holidays, trauma, weather, illness or supply disruptions. State event dates and effect assumptions. Do not fabricate live monitoring. Coordinate any new dependency through Person 3.

Write meaningful deterministic tests for site isolation, audited starting stock, expiry without double subtraction, dated supply/cancellation, no duplicated booked supply, scenario arithmetic, zero-demand handling and shortage accounting. Use fixed dates and fixture inputs; tests must not overwrite tracked data or a shared state file. Smoke-test the outlook against the actual Person 2 API before handing off. If an API is pending, use contract fixtures in tests, record the dependency, and complete integration when it lands; do not ship a second store.

Finish with a reviewable commit on your feature branch. Report changed files, exact tests run and results, the reproducible scenario, assumptions and unresolved dependencies. Hand Person 3 your commit/branch for integration into `bloodsight`; do not merge into main or deploy. Work until the forecast slice is usable and verified, with P1 omissions clearly listed.
