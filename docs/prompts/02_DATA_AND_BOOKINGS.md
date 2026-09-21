# Person 2 — Shared data, inventory, matching and bookings

Copy the assignment below into your coding assistant.

---

Implement the shared data workstream for **BloodSight AI** in https://github.com/Julicorn134/MainHackathon. Continue the existing Python/Streamlit prototype from the latest `origin/bloodsight`. Use your own clone/worktree and create `feat/bloodsight-data`; inspect and preserve existing changes. Main still contains the earlier TrialMatch plan.

Read `docs/source/BloodSight-original.pdf`, `docs/BLOODSIGHT_REQUIREMENTS.md`, `docs/BLOODSIGHT_TEAM_PLAN.md`, and `docs/BLOODSIGHT_CONTRACTS.md`. Build and test the P0 demonstration with synthetic data only. The proposed contract is yours to implement and maintain; communicate justified changes before other people implement consumers. Do not replace the application architecture or add an external database/service for this hackathon.

You own `bloodsight/store.py`, new `bloodsight/inventory.py` or `bloodsight/fixtures/` files, `bloodsight/tests/test_store*.py`, `bloodsight/tests/test_inventory*.py`, and `docs/BLOODSIGHT_CONTRACTS.md`. Person 1 owns forecasting/history; Person 3 owns common/staff UI and dependencies; Person 4 owns the donor UI. Do not edit their files to resolve integration problems.

Start by inspecting existing APIs, fixtures and JSON persistence. The store already has consent/preferences, a synthetic population, matching counts, requests, notifications, bookings and lab data. Keep useful code and stable public signatures. Publish the minimal new callable interfaces and return shapes early so the other people can continue independently.

Implement P0 in this order:

1. Add the contract's `inventory_snapshot`, `record_inventory_audit`, `inventory_expiries`, `available_slots`, `scheduled_supply`, and `place_details`. Give pending consumers deterministic fixtures immediately, then complete their logic. Keep source/dates/product/unit assumptions explicit.
2. Seed facility-specific lots and audit timestamps for `rbc`, `mumc`, `heerlen`, coordinated with Person 1's closing stocks. Support manual replacement audits, available/quarantined lots, expiry, stale reports and missing-as-unknown stock. Validate counts/types/dates and restrict mutations to the user's organisation. Existing state files need backward-compatible defaults or a deliberate version migration, not silent data loss.
3. Use one consistent matching policy for suggestions, notifications and booking. Apply exact requested type, synthetic distance, preferences/consent, pause, place opt-out, demo next-eligible date/interval and new-outreach contact limits. Explain that the 56-day interval and current response rate are demo settings, not universal rules. Reaching a contact cap after an invitation must not hide that already-issued invitation.
4. Harden `book(username, request_id, slot)` against nonexistent/closed requests, unoffered/past/full slots, mismatch and conflicting appointments. Preserve the signature. Repeated clicks must produce one active booking. Cancellation must respect ownership and remove expected supply. Keep synthetic population bookings deterministic, capacity-aware and clearly separated from interactive demo accounts.
5. Make `send_request` idempotent, cap repeated outreach and deduplicate notifications. Closing a campaign prevents new sign-ups but retains existing appointments. Staff receive appropriate in-app booking/cancellation updates. Keep unbooked donor names private and keep lab report fields out of centre campaign data.
6. Return dated incremental campaign supply with booking IDs, collection/usable dates, expected units and source. Include bookings from closed campaigns; exclude cancellations and past collected appointments. Preserve `expected_donations` compatibility, deriving it from the same schedule. Distinguish routine supply from incremental campaigns to prevent forecast double counting. Provide clearly fictional contact details; no real email/SMS.

Do not claim atomic JSON replacement makes concurrent read/modify/write operations transactional. Keep this a local demo and document limitations. Centralise mutations and add proportionate protections for simultaneous sessions; do not widen the task into production infrastructure.

Use a temporary `BLOODSIGHT_STATE` path, set before importing the store, and fixed dates for tests. Cover an opt-out, pause, wrong type, radius, existing invitation at contact cap, invalid/full slot, duplicate booking/send, cancellation ownership, closed-campaign supply, expiry/quarantine counts, repeated audit replacement and permission checks. Use representative boundary cases rather than tests that simply repeat implementation details. Run the real forecast/donor consumers after their branches are ready; do not leave only stub APIs.

Finish with a reviewable commit on your feature branch, updated contract, fixture/migration notes and actual test results. Tell each consumer what to call and provide Person 3 the commit/branch for integration into `bloodsight`. Do not merge main or deploy. Complete the shared slice before spending time on optional features.
