# Person 4 — Donor portal

Copy the assignment below into your coding assistant.

---

Extend and verify the donor portal for **BloodSight AI** in https://github.com/Julicorn134/MainHackathon. Continue the existing Python/Streamlit application from the latest `origin/bloodsight`. Use your own clone/worktree and create `feat/bloodsight-donor`; inspect and preserve local changes. Do not start from TrialMatch on main or build a separate app.

Read `docs/source/BloodSight-original.pdf`, `docs/BLOODSIGHT_REQUIREMENTS.md`, `docs/BLOODSIGHT_TEAM_PLAN.md`, and `docs/BLOODSIGHT_CONTRACTS.md`. The PDF's patient section mostly describes donor actions. Build the P0 donor journey using test data and the existing `patient` role. This is an implementation task: finish a usable portal and verify it.

You own `bloodsight/views/patient.py`, new `bloodsight/views/donor_*.py` helpers and `bloodsight/tests/test_donor*.py`. Person 2 owns store/matching/booking; Person 3 owns shared UI/login/dependencies; Person 1 owns forecasts. Request needed API changes rather than modifying their files or creating a second store.

Commit `a99d91a` adds a substantial `views/patient.py`: Results and value charts, matching Needs, booking/decline, Donations/history, a rule-based Ask screen, Notifications and Me/preferences. Preserve and extend this implementation. Existing store methods cover these flows; read their signatures and return values. Known gaps include missing capacity-aware slots and booking error handling, no cancellation button on the Donations screen, missing requested quantities/contact details, and an unknown blood type defaulting to the first known type. Use shared `ui` helpers and Person 2's `available_slots`/`place_details` contract. Keep `render(user)`.

Build P0 in this order:

1. Needs: show open matching requests from `store.needs_for(username)` with facility, synthetic distance, requested blood type/amount, urgency, reason this donor sees it, slots and clearly fictional contact details. Give useful empty states for no match, paused/opted-out preferences and closed requests. Include a visibly simulated emergency example; do not create a real emergency alert.
2. Booking: select an offered available slot and confirm with at most two actions after the card. Call `store.book` and display success only when it succeeds. Handle full/past/invalid slots and stale state gracefully. Reread state after a mutation. A UI click must not create duplicate bookings. Provide “Not this time” and hide declined requests appropriately without exposing the donor's identity to staff.
3. Donations: show upcoming bookings, place/session details, cancellation and recorded synthetic donation history/count/volume where available. Campaign closure must not make an active booking disappear. Keep appointments separate from completed donations. Do not turn bookings or units into an unsupported patients-saved count. Optional badges come after the complete loop works.
4. Notifications: show this user's inbox, unread state, mark-read and clear booking/request updates. Use store operations; never write JSON. Messages remain inside the demo.
5. Me/preferences: show blood type and history, allow the existing opt-in switches, place preferences and pause setting, with clear explanations. Save through `update_user`. A demo interval/next eligible date is a planning assumption, not a promise that the person may donate. Keep unknown blood type distinct from a confirmed type.
6. Preserve the existing Results, value charts and rule-based Ask features without expanding their scope. Label template/rule-based explanations accurately instead of “Written by the AI.” Keep own-record access and session isolation, and do not put lab values in campaign data. Do not add an LLM or invent new diagnostic or donor-eligibility answers; these extra features must not displace the PDF's donor workflow.

Use plain, compact screens with clear buttons, dates and empty states. Keep synthetic-data labelling visible. No map API, medical eligibility chatbot, real email/SMS, external link that sends a message, or production signup redesign is required. The existing demo donor `patient` has preferences enabled; `patient2` is the opt-out case. Both are synthetic.

Verify the actual shared store flow: staff creates/sends request → donor sees reason and notification → donor books → staff sees booking → donor cancels → future supply changes. Also verify opt-out/pause, wrong-type no-match, full-slot error, repeated clicks, unread counts, own-record privacy and a booked appointment after campaign closure. Use fixed fixtures and temporary `BLOODSIGHT_STATE`; add focused tests for transformations/guards you introduce and perform a browser smoke test of the journey. Do not merely test that static labels exist. If the shared API is pending, use contract fixtures in tests and record the dependency, then integrate the real API before completion.

Finish with a reviewable commit on your branch. Report screens delivered, tests/checks actually run, a short click-through demo and unresolved dependencies. Give Person 3 your branch/commit for integration into `bloodsight`; do not merge main or deploy. Complete P0 before optional rewards, chat or extra visual polish.
