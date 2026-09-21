# BloodSight AI: guide to the prototype as built

A hackathon prototype with three sides and one spine: the blood centre sees a shortage before it
happens, and the request reaches the right people in time. The centre gets a 14-day forecast per
blood type, a shortage alert, a what-if simulator and a sized recommendation, and turns that
recommendation into a donor request in two clicks. The request goes to the people who can answer
it: patients of the lab, people who gave at that place before, and people who live near it. The lab
publishes the day's results, holds back what an app may not deliver first, and passes one fact to
the donor side: the blood type of patients who switched the donor part on. The patient reads their
own results, gets a plain explanation of a value, sees why they of all people were asked, and books
a slot. All data in this repo is synthetic.

The **Data** pages now accept CSV history and JSON lab reports, save them in Supabase when configured,
and feed the forecast and AI evidence from saved records. See [cloud setup](../supabase/README.md)
and [data/AI setup](../docs/DATA_AND_AI.md). AI explanations require an OpenRouter or direct OpenAI key and a successful API response.

## Run it

Windows:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

macOS and Linux:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Streamlit opens the app at http://localhost:8501.

Demo accounts, requests, bookings, notifications and the bundled batch state are kept in `state.json`.
Deleting that file resets this local demonstration state on the next load. Imported history and
reports live separately in Supabase (or explicitly selected SQLite); this does not reset them.

```
del state.json          # Windows
rm state.json           # macOS and Linux
```

Set `BLOODSIGHT_STATE` to point at a different state file. Useful for a second copy of the demo, or
for a test run that must not touch the rehearsed state.

```
set BLOODSIGHT_STATE=C:\temp\demo2.json          # Windows, cmd
$env:BLOODSIGHT_STATE = "C:\temp\demo2.json"     # Windows, PowerShell
export BLOODSIGHT_STATE=/tmp/demo2.json          # macOS and Linux
```

`python forecast.py 2026-09-21` regenerates `data.csv`: 180 days of donations, usage and closing
inventory for 8 blood types, ending on the date you give (default: today). It prints the summary
table afterwards. The app takes its "today" from the last date in `data.csv`, so every screen agrees
with the forecast. The numbers quoted in this README and in `DEMO.md` are the ones the generator
produces for the end date 2026-09-21. A different end date shifts the weekday alignment and the
holiday positions, so the numbers move. Regenerate once, then rehearse on that file.

## Logins

| Username | Password | Role | What they see |
| --- | --- | --- | --- |
| centre | centre123 | Blood centre (Robin Vos, Regional Blood Centre) | Outlook, Requests, Bookings, Notifications |
| lab | lab123 | Lab and doctor (Dr. Imke Peters, Bloodlab Maastricht) | Publish results, Patients, Notify patients, Donor link, Notifications |
| patient | patient123 | Patient Alex Jansen, O-, lab code BL-4790, results and both donor switches on | Results, Needs, Donations, Ask, Notifications, Me |
| patient2 | patient123 | Patient Sam de Boer, A+, lab code BL-4802, results only | The same six pages, with an empty Needs page until a donor switch is turned on |

The login page has a button for each of the three demo accounts, so nobody has to type during a
pitch. A role only ever loads its own view module, so one side's pages never appear in another
side's sidebar.

The second tab of the login page, "First time? Use your lab code", signs a new patient up. The lab
code is the tie between an account and a set of lab reports. The page lists the demo codes that are
still free: `BL-4821` (an O- report) and `BL-4835` (a B+ report). Sign-up asks for a name, a
username, a password of at least six characters, a blood type (or "I do not know", which the
published lab result fills in), a postcode, and the three consent switches. An unknown code or a
code that already has an account is refused with a readable message.

These are demo credentials in a public repository. Passwords are salted and hashed with PBKDF2 in
`store.py`, but that is the only security measure in the app: there is no session expiry, no rate
limiting, no transport security and no access control beyond the role check. It is a prototype on
synthetic data, not a production system, and it must not be pointed at real patient data.

## The three sides

### Blood centre

- **Outlook.** Four figures at the top: units in stock, blood types at risk in 14 days, the earliest
  projected shortage, and the backtest error of the forecast. Then a card per blood type with
  current units, days of supply and a risk chip, and a table view of the same. Pick a blood type to
  get the alert, the 30-day history plus the 14-day projection with its uncertainty band and the
  safety and warning lines, a what-if simulator (additional donations, launch delay, campaign
  length), the recommendation with target, window, latest effective launch, priority and expected
  risk after the campaign, the drivers behind it, and an expander with the daily usage and donation
  curves plus the model description. If donations are already booked through open requests of this
  centre, they appear as a second projection line. The button "Turn into a donor request for O-"
  carries the blood type, the target and the window over to the Requests page.
- **Requests.** A form for a new request: blood type, distance, which days and times to offer as
  slots, the target number of donations, and the message people read (written for you, editable).
  While you fill it in, the right column shows how many people match, split into patients of the lab
  and people who gave at this centre before, plus the expected number of bookings and the matching
  rules in plain words. "Send to N people" sends it at once, "Save draft" keeps it for later. Below
  the form, every request of this centre: a draft can still be sent, a sent request shows day, asked,
  seen, booked and not this time, a progress bar against the target, and the bookings by name.
  "Simulate next day" moves a sent request one day along its response curve. "Close request" ends it.
- **Bookings.** Every sent request with the people who booked a slot: slot, name, blood type, a note
  on whether they gave here before, and whether the booking came from a real app account or from the
  simulated population. This is the only screen where the centre sees a name.
- **Notifications.** The centre's inbox. A booking arrives here the moment it is made.

### Lab

- **Publish results.** The day's batch as the lab system delivers it: 212 reports, 205 ready, the
  number of code mismatches and the number of urgent values. Then the held-back reports, one card
  each with the reason. An urgent one has two buttons: "Doctor has phoned" and "Release", and Release
  is disabled until the phone call is recorded. A code mismatch has "Checked by hand, release".
  "Publish 205 to patients" publishes the batch, which can only happen once. Below that, a preview of
  the value card the patient will see.
- **Patients.** The lab's own patients with an account: name, lab code, which switches are on,
  newest report, whether they are in today's batch. Below it, the lab codes that have a report but no
  account yet.
- **Notify patients.** Write a title and a message, pick "All patients", "Donors only" or "One
  patient", and see who will get it and how many before pressing "Send notification". Two one-click
  templates fill the form. Messages sent in this browser session are listed underneath.
- **Donor link.** What the lab passes to the donor side and what it does not. The count of patients
  in this batch with the donor part on, the accounts with the donor part on and the blood type each
  one passes, and an explicit list of what never leaves the lab: values, ranges, which tests were
  done, names, addresses and lab codes, and anything about a patient who did not switch the donor
  part on.
- **Notifications.** The inbox of the lab account.

### Patient

- **Results.** The newest published report: values outside the range the lab printed come first,
  the rest are folded into an expander. Every value card carries the number, the unit, the lab's own
  range and a flag. Opening a value gives the number large, a chart of that value across this
  person's own tests with the lab's minimum and maximum, an optional live AI explanation, the
  source line (report date and line number), and a "Summary for my doctor" download: a plain-text
  page with the out-of-range values, their ranges and their history. If the donor part is on and something is open nearby, a card at the bottom
  bridges to Needs.
- **Needs.** One card per open request this person may see, most urgent first. Each card names the
  place, the blood type, the distance, the urgency and, under "Why you", the reasons this person was
  matched. Booking is one click on a slot. "Not this time" hides the card and is never shown to the
  place. An expander explains what happens at the visit. A toggle pauses all requests. If both donor
  switches are off, the page says so and shows nothing.
- **Donations.** How many donations and at how many places, the slots currently booked, the
  donation history with where each one went, and a per-place switch: whether that place may ask.
- **Ask.** A question form calls the configured AI provider with this person's permitted results and donor context.
  Answers show the supplied source records. No key or provider failure produces an availability
  message. The model is instructed not to diagnose, infer causes or promise donation eligibility;
  source checks are not a guarantee of medical correctness.
- **Notifications.** Everything the lab and the places sent, newest first, with a "Mark all as read"
  button. The unread count sits in the sidebar.
- **Me.** The three consent switches, the pause toggle, the postcode and the blood type, and the lab
  code this account is tied to.

## Notifications

| Who creates it | Action | Who receives it |
| --- | --- | --- |
| Blood centre | Sends a request (new or a saved draft) | Every patient account that matches the request and has been asked fewer than twice this month |
| Lab | Publishes the batch | Every patient account with a report in the batch and the results switch on |
| Lab | Writes a message to "All patients" | Every patient with the results switch on |
| Lab | Writes a message to "Donors only" | Every patient with at least one donor switch on and not paused |
| Lab | Writes a message to "One patient" | The selected patient |
| The app | A patient books a slot | The patient, with what to bring to the visit, and every centre account belonging to the place that asked |

## The rules the app keeps

These are enforced in `store.py`, not only written on a screen.

- **Consent switches.** Nobody is asked unless they switched it on. Three separate switches: show my
  results, tell me when a place nearby needs my blood type, tell places I gave to before. A pause
  stops everything, and a per-place switch stops one place. Results only is a valid way to use the
  app: with both donor switches off, Needs stays empty and says so.
- **Counts, not names.** A place asks how many people of a blood type it could reach within a
  distance and gets a number. The matching step never returns names.
- **A name appears only on a booking.** The moment a person books a slot, and not before, the place
  learns their name and the slot they chose.
- **"Not this time" is only a count.** A decline is stored as an input to a count. No screen of the
  place shows who declined.
- **At most two request notifications a month.** The counter is checked before a request
  notification is sent, and people already at the limit are excluded from the match count. Open
  needs stay listed on the Needs page. The counter is not reset by the prototype.
- **One open request per place and blood type.** A second send for the same type is refused until
  the first is closed, so the same people are not asked twice and bookings are not counted twice.
  A request closes itself when bookings reach its target.
- **Closing a campaign keeps booked appointments.** The people who booked are told their slot
  stands. A cancellation tells both the person and the place.
- **Urgent values wait for the doctor's phone call.** An urgent lab value is held back from the
  batch. The Release button is disabled until the phone call is recorded, and the store raises an
  error if a release is attempted anyway. An app never delivers an urgent value first.
- **AI scope.** Instructions limit answers to the supplied evidence and prohibit diagnosis,
  treatment advice and eligibility decisions. The app validates cited source IDs; model behavior
  still needs evaluation. This is not a deterministic medical-safety rule in `store.py`.
- **Donation eligibility.** The need card says the centre does a health check at the visit and
  makes the final call. AI output cannot establish eligibility.

## How the forecast works

Per blood type, two ridge regressions (usage, donations) on the last 42 days with day-of-week,
trend and public-holiday features. Projected inventory = current inventory + predicted donations
minus predicted usage. The band around the projection is the residual spread of the two fits, widened
with the square root of the days ahead, because daily errors accumulate in a running balance.
Thresholds are days of supply at the 90-day average usage: under 3 days is critical, under 5 days
is medium. Campaign units become usable 4 days after launch (outreach, then testing and processing).
The recommended size is the smallest campaign, found by simulation in steps of 10 units, that avoids
the shortage and ends the 14 days above the warning level; if no campaign does that, the smallest
one that at least avoids the shortage. The "latest effective launch" is the day the shortage is
projected minus those 4 days. The backtest hides the last 14 days, refits, and reports the error on
total usage over those days, averaged over the eight blood types for the figure at the top of the
Outlook page.

Not modelled: unit expiry (42-day shelf life), cross-type substitution, transfers between centres,
the difference between whole blood and plasma in the inventory, and any feedback from a campaign on
later donations. Booked donations from open requests are added to the projection as extra units on
the same lead time as a campaign; nothing else from the request side changes the forecast.

## What is simulated

Everything in this repository is synthetic. There is no real patient, no real donor and no real
blood centre.

- **The population's responses to a request.** `data.csv` covers stock, not people. The people a
  request could reach come from a synthetic population of 120,000 rows generated in `store.py`:
  blood type, distance, consent, days since last donation, asks this month, and whether they gave at
  this place before. The match count is a filter over that array. After a request is sent, the
  asked, seen, booked and not-this-time figures come from a fixed five-day response curve, and
  "Simulate next day" steps along it. Booking names other than the real app accounts are drawn from
  a small name list. Everything a real app account does is live and sits on top of the simulated
  numbers, and the bookings table says which is which.
- **The lab batch totals.** 212 reports, 205 ready, 38 with the donor part on, and the seven
  held-back reports are constants in `store.py`. The four full reports behind them (Alex, Sam, and
  the two unclaimed lab codes) are real data structures with 18 values each, and those are the ones
  that actually appear on a patient screen.
- **Distances from postcodes.** A real system would geocode. A new sign-up gets stable pseudo
  distances drawn from a seed derived from the postcode, so the same postcode always gives the same
  distances. The two seeded patients have fixed distances.
- **The assistant and the explanations.** No language model runs in this prototype. The value
  explanation and the answers in Ask are built from a fixed dictionary of plain-language
  descriptions, one sentence per value, plus this person's own numbers and trend, plus keyword rules
  that catch a question about a diagnosis, a cause or permission to donate and return the refusal.
  The screens say so where the text appears.

## Files

- `app.py`: Streamlit entry point. Sets the page up, requires a login, imports the view module for that role.
- `login.py`: login page, the three demo-account buttons, and the lab-code sign-up form.
- `ui.py`: shared colours, CSS, status chips, page header, sidebar navigation, notification list.
- `store.py`: the data layer. Accounts, consent switches, requests, matching, bookings, declines, notifications, lab batch and reports. Holds the privacy rules and reads and writes `state.json`.
- `forecast.py`: synthetic data generator, ridge-regression forecast, thresholds, risk assessment, campaign sizing, backtest. Also a command-line script that regenerates `data.csv`.
- `views/outlook.py`: the blood centre's Outlook page: figures, cards, chart, what-if, recommendation.
- `views/centre.py`: the blood centre's sidebar and its Requests, Bookings and Notifications pages.
- `views/lab.py`: the lab's Publish results, Patients, Notify patients, Donor link and Notifications pages.
- `views/patient.py`: the patient's Results, Needs, Donations, Ask, Notifications and Me pages, including the explanation text and the rule-based assistant.
- `data.csv`: 180 days by 8 blood types of donations, usage, closing inventory and a holiday flag. Generated by `forecast.py`.
- `state.json`: everything that changes while the demo runs. Not in version control. Delete it to reset.
- `requirements.txt`: streamlit, pandas, numpy, plotly, scikit-learn.
- `.streamlit/config.toml`: light theme and the app's colours.
- `tests/ACCEPTANCE.md`: the acceptance checks, written before the three sides were built.
- `docs/sketches/`: the screen sketches and the script that generated them.
- `DEMO.md`: the three-minute demo script.
