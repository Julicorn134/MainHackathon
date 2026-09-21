# Person 3 — Staff dashboard and team integration

Copy the assignment below into your coding assistant.

---

Implement the staff interface and coordinate integration for **BloodSight AI** in https://github.com/Julicorn134/MainHackathon. Continue the existing Python/Streamlit app from the latest `origin/bloodsight`. Use your own clone/worktree and branch `feat/bloodsight-staff`; preserve existing work. Main's TrialMatch plan is historical.

Read `docs/source/BloodSight-original.pdf`, `docs/BLOODSIGHT_REQUIREMENTS.md`, `docs/BLOODSIGHT_TEAM_PLAN.md`, and `docs/BLOODSIGHT_CONTRACTS.md`. Deliver the P0 synthetic-data demonstration, with a clear interface suitable for manual reporting and limited bandwidth. Do not claim offline sync, live monitoring or an organisational partnership. Implement and verify the app; do not stop at a proposal.

You own `bloodsight/app.py`, `bloodsight/login.py`, `bloodsight/ui.py`, `bloodsight/views/centre.py`, `bloodsight/views/lab.py`, `.streamlit/`, `requirements.txt`, README files, acceptance/demo docs and integration tests. Person 1 owns `forecast.py`, history and `views/outlook.py`; Person 2 owns store/inventory/contracts; Person 4 owns `views/patient.py`. Coordinate shared changes instead of overwriting their files.

The latest reviewed commit is `a99d91a`, which adds a substantial donor portal and centre/lab tweaks. Existing staff pages show Outlook, Requests, Bookings and Notifications. Centre/outlook still hardcode `rbc`. The previous acceptance checklist contains aspirational outcomes and fixed numbers, not proof of passing behaviour. Preserve the new donor implementation; Person 4 is extending and verifying it.

Build P0 in this order:

1. Preserve role routing, demo accounts and the existing `views.outlook.render(user)` call. Resolve staff organisation from the logged-in user. Keep region-wide read visibility separate from permission to edit a facility's stock/campaigns. Finish the staged prefill/rerun navigation with Person 1 so normal handoff does not depend on catching a Streamlit widget-state exception.
2. Add simple Inventory and Regional overview screens using Person 2's APIs: facility/type/product, usable units, excluded expired/quarantined stock, expiring-soon amount and last audit. Show missing/stale data honestly. Provide a compact manual synthetic lot/audit form; validate through the store. Avoid maps or extra downloads when a table is clearer.
3. Connect forecast recommendation to the existing Requests form via the agreed prefill including `place_id`. Staff can review type, target, sessions/capacity, synthetic radius, message and simulated urgency before sending in-app. Show aggregate matches and actual synthetic-account activity separately from modelled population responses. Do not invent campaign success statistics.
4. Keep draft/send/close and booking views usable. Show booked appointments after campaign closure, meaningful no-data states, and clear validation messages. Repeated rerenders must not send invitations/alerts again. Use Person 2's deduplication path for shortage notifications instead of directly mutating JSON.
5. Keep existing laboratory workflows working and isolated from centre campaigns. The PDF does not require expanding lab AI/chat. Label static sample explanations as such. Escape user-supplied content in shared notification rendering. Keep a visible synthetic-demo label and distinguish booking, expected donation and usable stock.

You are also the integrator. During the first 20 minutes, confirm contracts and owners; by around hour two, combine a working forecast → request → donor booking → updated staff outlook path. Review contributor branches and integrate into `bloodsight` in small steps once their checks pass, preserving their commits. Coordinate conflicts with owners; do not blindly replace files. Do not merge into main or deploy as part of the hackathon build. Only add/pin dependencies that the implementation actually needs and verify a fresh environment.

Test the combined app with two isolated browser sessions and a fresh temporary `BLOODSIGHT_STATE`. Exercise all three roles. Record observed results for correct facility prefill, expiry/stale stock, matching/opt-out, invalid/full slots, booking/cancel, closed-campaign appointment retention, dated forecast supply and non-booking identity privacy. Verify meaningful forecast arithmetic with Person 1 rather than asserting an old fixed 210-unit example. Run relevant automated tests from all four workstreams; log failures as failures.

Update the README to actual run steps, accounts, files and limitations. Replace outdated acceptance expectations only where the agreed requirements changed; do not remove a failing requirement to manufacture a pass. Add a short demonstration script using reproducible fixture values, plus a results log distinguishing automated checks, browser checks and unverified items. Produce a usable 90-second presentation of the complete loop.

Finish with your reviewable commit and an integrated `bloodsight` build when the other branches are ready. Report included commits, checks actually run, demo instructions and remaining P1 scope/risks. No real messages, data, external healthcare integrations or clinical validation claims.
