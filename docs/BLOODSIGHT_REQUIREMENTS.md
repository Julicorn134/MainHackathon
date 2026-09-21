# BloodSight AI: requirements and implementation scope

## Source and interpretation

The source is the three-page [BloodSight Google Docs PDF](source/BloodSight-original.pdf), supplied by the project owner and preserved unchanged. Its vision is to anticipate shortages and plan targeted donor campaigns: **Predict. Prepare. Prevent Shortages.**

This Markdown file translates the brief into buildable work. Priority, ownership, interfaces, and the four-hour cut are implementation recommendations, not extra text from the PDF. Earlier project discussion also requires **test data** and an intended benefit for services in lower-resource settings, without assuming an organisational partnership or real-world validation.

The source's “FOR PATIENTS” section mostly describes donor actions; this plan calls it the donor portal. The last page ends with an unfinished “FEATURES OF OUR PLATFORM” bullet, “C”. It provides no additional usable requirement.

## Four-hour outcome

Demonstrate one complete loop: staff see a forecast shortage for a blood type at a facility, check dated usable stock, create an invitation, a synthetic opted-in donor books a slot, and expected supply changes on the appropriate future date. Explain the forecast and invitation, and allow a +50/+100/+200 what-if comparison.

Use a small reproducible fixture with the existing three place IDs and eight blood types. Make the selected facility explicit. Show stale manual reports; remain usable without live integrations. This is a testable design hypothesis for limited-resource workflows, not a claim that a particular country lacks systems or that the product has been validated there.

## Source requirements and delivery decisions

P0 is the integrated demonstration. P1 extends it only after the loop works. Future items need data or partners beyond this hackathon. Every source feature is retained below even where implementation is deferred.

| ID | Source requirement | PDF page | Delivery decision | Owner |
| --- | --- | --- | --- | --- |
| R01 | Demand by blood type and location | 1 | P0: 14-day synthetic forecast with facility selector | 1 |
| R02 | ML on historic donations and transfusion requests | 1 | P0: retain ridge baseline; compare with a simple baseline on synthetic holdouts | 1 |
| R03 | Seasonal dips, holidays, summer | 1 | P0: disclose configured calendar assumptions; P1: longer seasonal history | 1 |
| R04 | Admissions and local trauma patterns | 1 | P1: synthetic covariates/scenarios; future real feeds | 1 |
| R05 | Match possible donors for contact | 1 | P0: consent, exact requested type, distance, pause, demo interval and contact cap; in-app invitations | 2, 4 |
| R06 | Severe weather and disasters affecting drives | 1 | P1: labelled simulated event with dates and effects; future live monitoring | 1 |
| R07 | Public health outbreaks and seasonal illness | 1 | P1: labelled demand/turnout scenario; future live data | 1 |
| R08 | Global supply-chain trends | 1 | Future feed integration; P1: transparent simulated disruption | 1 |
| R09 | Daily audits, current counts, expiry dates | 1 | P0: synthetic lots and audit time; exclude expired/unusable stock; no live-sync claim | 2, 3 |
| R10 | Threshold notices and advance shortage alerts | 1 | P0: dated dashboard/in-app warnings; deduplicate reruns | 1, 2, 3 |
| R11 | Shared hospital/clinic inventory | 1 | P0: regional table and freshness; future real network integration and transfers | 2, 3 |
| R12 | Campaign recommendations: when and where | 1 | P0: facility, type, units, timing and explanation | 1, 3 |
| R13 | Appointment donations versus projected demand | 1 | P0: dated supply with disclosed yield/delay; no double counting | 1, 2 |
| R14 | What-if demand, turnout, +50/+100/+200 donations | 2 | P0: donation presets; P1: demand and turnout controls | 1 |
| R15 | Management dashboard | 2 | P0: forecast, stock freshness, risks, campaigns, appointments | 3 |
| R16 | Emergency notices after disasters/accidents | 2 | P0: explicitly simulated urgent request; P1: event-driven scenario | 2, 3, 4 |
| R17 | Nearby hospitals and quantities needed | 2 | P0: facility, synthetic distance, quantity, available appointments | 4 |
| R18 | Amount/history, rewards and patients saved | 2 | P0: synthetic donation count/volume; P1: badges; no unsupported patients-saved number | 4 |
| R19 | Donation locations and booking | 2 | P0: sessions, capacity, book and cancel | 2, 4 |
| R20 | Donation frequency/history and specific type | 2 | P0: own history/type; demo next-eligible date is not medical clearance | 2, 4 |
| R21 | Contact the blood bank | 2 | P0: visibly fictional contact details or in-app message | 2, 4 |
| R22 | O-negative, October 8–15, 180-unit example | 2 | Illustrative only; actual demo values come from fixture calculations | 1, 3 |
| R23 | National/regional/hospital services and emergency organisations | 3 | Target audience; P0 shows a small regional network | 3 |
| R24 | B2B SaaS priced by facility/region/data volume | 3 | Business concept; billing and production multi-tenancy are future work | 3 |

The source's “patients saved” reward cannot be derived from donation count alone. Showing contributions preserves useful feedback; a later impact estimate needs an explicit defensible method and an estimate label.

## Existing code and gaps

Baseline reviewed through `a99d91a` on `bloodsight`, 21 September 2026, including the latest expanded patient view and centre/lab changes. These are source observations, not a browser acceptance report.

| Area | Existing work | Gap |
| --- | --- | --- |
| Forecast | Synthetic history, ridge models, 14-day projection, thresholds, campaign sizing, one holdout | Facility dimension, dated appointments, expiry, transparent assumptions and validation |
| Staff | Outlook, request creation, matching counts, booking list, notifications | Inventory/network pages, selected organisation, end-to-end verification |
| Data | JSON store, synthetic population, preferences, appointments, notifications | Consistent guards, slot capacity, repeated-send protection, dated supply and lots |
| Donor | Results, matching needs, booking/decline, history, preferences, inbox, rule-based Ask | Slot capacity/error handling, cancel from booked-history screen, requested quantities/contact, unknown blood type handling and verification |
| Lab | Demo publication and notifications | Preserve as extra existing scope; not a new PDF requirement |
| Tests | Written acceptance checklist | Execute/update it; fixed numbers and implemented screens do not establish that checks pass |

Source-level issues to verify: centre/outlook hardcode `rbc`; history lacks facilities; expected donations use a fixed window and omit closed campaigns; bookings lack full slot/matching/capacity guards; repeated sends may repeat notifications; the 56-day donation interval and 9% booking response are demo assumptions. The donor form defaults an unknown type to the first known type, and template explanations have an AI heading. The forecast/request handoff currently catches a Streamlit state error and should use a staged navigation change. Atomic JSON file replacement is not a transactional database.

## Build constraints

- Extend Python/Streamlit. No framework rewrite, credentialed dataset, paid API, LLM or live feed is required.
- All accounts, stock, histories, events, distances and messages are synthetic/simulated. Keep this visible.
- Prioritise manual entry, timestamps, readable tables and low data volume. Offline sync, SMS, localisation and real deployment are future work; do not advertise them as implemented.
- Distinguish usable stock, projected balance, unmet demand, expected donations and appointments. Do not hide unmet demand by clipping a chart at zero.
- Use explicit dates, units and planning assumptions. A donor match suggests an invitation; it does not determine medical eligibility. Use exact-type matching in the MVP.
- No real outreach, real patient data, autonomous transfers or claims of validated clinical performance.

## Integrated acceptance

1. A fresh fixture has a stable shortage and adequate-stock case. Staff select facility/type and see the 14-day forecast, data date and assumptions.
2. Stock shows usable units, expiry exclusions and audit time; stale reports are labelled. Regional totals reconcile with lots rather than copying aggregate stock across sites.
3. Forecast prefill opens the correct facility/type campaign. The invitation shows purpose, amount and available sessions.
4. A matching opted-in donor sees the request and reason. Opted-out, paused, wrong-type and out-of-radius donors do not. Contact limits apply consistently.
5. Booking updates both views once. Invalid/full slots are rejected. Cancellation removes future supply; campaign closure retains booked appointments.
6. Supply changes only on its expected usable date and is not added again on rerender. +50/+100/+200 scenarios are labelled incremental assumptions.
7. Donors see only their own records. Staff do not see non-booking donor names or donor lab results on campaign screens.
8. Record a reproducible demo, actual test results, deferred requirements and remaining limitations.

See [ownership and schedule](BLOODSIGHT_TEAM_PLAN.md) and [shared contracts](BLOODSIGHT_CONTRACTS.md).
