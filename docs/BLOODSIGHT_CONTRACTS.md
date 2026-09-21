# BloodSight shared contracts

**Proposed implementation contract, not a list of functions already implemented.** Based on source through `a99d91a`. Person 2 owns revisions and communicates adjustments before consumers implement them. Preserve existing public APIs and add optional arguments where possible.

## Conventions

- Place IDs: `rbc`, `mumc`, `heerlen`. Blood types: `O+`, `O-`, `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`. Preserve existing `ANY_TYPE` behaviour, but use exact-type scenarios with one explicitly declared product for the MVP; do not mix product inventories.
- Date-only values: `YYYY-MM-DD`. Keep existing slot strings `YYYY-MM-DD HH:MM`, in an explicit configurable demo timezone. Audit timestamps include timezone. Calculations use `store.today()` as the demo date.
- Bookings have assumed yield and processing delay; they are not current stock. Defaults are labelled planning assumptions, not medical rules.
- State belongs in the store. UI code never writes JSON directly. Validation raises readable `ValueError` messages; UI catches them without showing false success.
- Tests set `BLOODSIGHT_STATE` before importing the store. JSON is a single local demo store; production multi-process reliability is not a delivered feature.

## Existing APIs

`store.PLACES`, `BLOOD_TYPES`, `today`, `authenticate`, `update_user`, `register_patient`, `requests`, `get_request`, `create_request`, `send_request`, `close_request`, `match_count`, `request_stats`, `request_bookings`, `needs_for`, `book`, `cancel_booking`, `decline`, `my_bookings`, `donations`, `notifications`, `mark_read`, `send_message`, `reports_for`, and `value_history` already exist. Read their actual signatures before use.

Keep `book(username, request_id, slot)` and `cancel_booking(username, booking_id)` callable. Validate inside the store, not only forms. Keep `create_request` compatible and add optional capacity settings with defaults. Repeated sends/bookings must not duplicate notifications or active bookings. Campaign closure stops new bookings but preserves existing appointments.

Matching consistently applies type, synthetic distance, preferences/consent, pause, place opt-out, demo interval/next-eligible date, and contact cap. The cap governs new outreach: an already-invited donor can still see and book that invitation after reaching the cap. Label anonymous population estimates separately from actual synthetic account matches. Staff see donor identities only for their bookings.

## New inventory APIs — Person 2

```python
inventory_snapshot(place_id: str | None = None) -> list[dict]
record_inventory_audit(actor: str, place_id: str, lots: list[dict],
                       reported_at: str) -> None
inventory_expiries(place_id: str, blood_type: str,
                   horizon: int = 14) -> list[dict]
```

Snapshot rows: `place_id`, `blood_type`, `product`, `usable_units`, `expired_units`, `quarantined_units`, `expiring_7d_units`, `last_reported_at`, `is_stale`. Missing stock is unknown, not zero. Display the configured stale threshold (24 hours is a demo default).

Audit lots: `lot_id`, `blood_type`, `product`, integer `units >= 0`, `expires_on`, `status` (`available` or `quarantined`). An audit replaces that facility's lots, never adds the same count again. Validate dates/types/nonnegative units and actor permissions. MVP convention: a lot is unavailable beginning on `expires_on` in the demo timezone. Store audit provenance; exclude expired/quarantined stock.

`inventory_expiries` returns currently usable lots expiring within the horizon as `{lot_id, expires_on, units}`. Person 1 uses an explicit first-expiring-first-out demand model so units consumed before expiry are not also subtracted as expired. Future supply requires a disclosed shelf-life assumption or explicit limitation. Never subtract expiry twice.

Person 2 seeds closing stock from Person 1's latest facility/type history. A manual audit overrides historical closing stock; the outlook displays its date and any discrepancy. Stale reported stock is not labelled current live stock.

## New appointment/contact APIs — Person 2

```python
available_slots(request_id: str) -> list[dict]
scheduled_supply(place_id: str, blood_type: str) -> list[dict]
place_details(place_id: str) -> dict
```

- Slots: `{slot, capacity, booked, remaining}`. Include active simulated/interactive bookings. The store validates offered future slot, request status, matching, capacity and conflicting active appointments. Rebooking the same appointment is idempotent.
- Supply: `{booking_id, request_id, collection_date, available_date, expected_units, source}` for active booked donations, including closed campaigns. Exclude cancellations; past collected appointments are not future supply. `source` is `interactive_demo` or `simulated_population`. Explain yield/delay. Each booking appears once.
- Place details: existing place fields plus `contact_label`, `contact_value`, `contact_is_demo: true`. Use clearly fictional contact information; no external delivery.

Keep `expected_donations` compatible but derive it from dated supply, retaining closed-campaign appointments. Consumers migrate to `scheduled_supply`. Shortage notifications use a stable deduplication key (facility/type/forecast-run/threshold); rerendering does not repeat them.

## Forecast APIs/data — Person 1

Add `place_id` to history, retaining `date`, `blood_type`, `donations`, `demand`, `inventory`, `holiday`. Unique key: `(place_id, blood_type, date)`. Legacy rows without a site belong only to `rbc`. Never copy aggregate totals to every site. Generate distinct reproducible histories; record seed, date and assumptions.

Keep existing positional calls to `load_data`, `forecast_type`, `thresholds`, `apply_campaign`, `assess`, `recommend`, `backtest`, `summary_table`. Add an integrated wrapper:

```python
forecast_for_place(df, place_id: str, blood_type: str, *,
                   stock: dict | None = None,
                   appointments: list[dict] | None = None,
                   expiry_lots: list[dict] | None = None,
                   horizon: int = 14)
```

Filter to one site before fitting. Inputs come from the APIs above. Return a DataFrame retaining `date`, `demand`, `donations`, `raw`, `inventory`, `low`, `high`, `band`, with explicit `scheduled_units`, `expiry_units`, `unmet_demand`. Document whether `raw` is cumulative balance or physical stock; do not confuse unmet-demand debt with later inventory.

For the demo, historic donations predict routine supply. Dated campaign bookings are incremental and added once on `available_date`. Routine appointments must be tagged/excluded from that increment until a replacement model exists. What-if units are additional assumptions and never persist as bookings or stock. Remove the old total-bookings overlay when using this wrapper.

Explain expiry, shortage handling, interval bands and synthetic validation. The 180-day fixture does not demonstrate annual seasonality.

## UI handoff — Persons 1 and 3

Keep `views.outlook.render(user)` and its existing caller. Prefill retains existing keys and adds the facility. The outlook stages a handoff and reruns; it must not assign the `nav` widget's state after that widget has been created:

```python
st.session_state['request_prefill'] = {
    'place_id': selected_place,
    'blood_type': blood_type,
    'target': recommendation['target_units'],
    'window': recommendation['window'],
    'days_to_safety': recommendation['days_to_safety'],
}
st.rerun()
```

Before building the sidebar, the centre view detects this prefill and sets `nav` to `Requests`, as the latest centre code already attempts. Consume the prefill once in the form and remove the need to catch a Streamlit state exception for normal navigation. The form validates organisation permissions; legacy missing `place_id` defaults to `user['org']`. Donor pages use `needs_for`, `available_slots`, `book`, `my_bookings`, `cancel_booking`, `donations`, `notifications`, `mark_read`, `update_user`, `place_details`. Shared `ui.py` belongs to Person 3; donor helpers belong in `views/donor_*.py`.
