# Three-minute demo script

For a live pitch. Three browser tabs, one for each side. A tab keeps its own login, so all three
stay logged in at the same time.

## Before you start

1. Delete `state.json` so the demo starts clean.
2. `.venv\Scripts\streamlit run app.py` (Windows) or `.venv/bin/streamlit run app.py`.
3. Open http://localhost:8501 in three tabs. On the login page each tab has a demo button under
   "Demo accounts": press **Blood centre** in tab 1, **Lab / doctor** in tab 2, **Patient** in tab 3.
4. Leave tab 1 on **Outlook**, tab 2 on **Publish results**, tab 3 on **Results**.
5. Check that `data.csv` ends on 2026-09-21. If not, run `python forecast.py 2026-09-21` before the
   pitch, or the numbers below will not match. The app's "today" is the last date in that file.

A tab only redraws when you click in it. When you switch back to a tab, click its page in the
sidebar once so it picks up what the other tabs did.

## 0:00 to 1:10. Tab 1, the blood centre sees it coming

Say: this is the regional blood centre on an ordinary Monday.

Point at the four figures at the top of **Outlook**:

- Units in stock: **2,856**
- Blood types at risk (14 days): **4 of 8**
- Earliest projected shortage: **O- in 7 days**
- Forecast error (14-day backtest): **10.0%**

Point at the O- card in the grid: **184 units**, **5.0 days of supply**, a red **Critical** chip,
and under it "below safety in 7 days". Say: there is no shortage today. Seven of these cards are
about the present. This one is about the future.

The blood type selector is already on O-, because the page opens on the worst one. Read the alert:

> Potential O- shortage detected. No shortage today: **184 units** in stock. Projected to fall under
> the safety threshold of **100 units** in **7 days**, reaching **80 units** a week from now.

Right of the chart, under **What-if: donor campaign**, drag **Additional donations** to **210**. The
line under the chart changes to:

> With +210 donations: Low, shortage avoided, stock back above the warning level
> Projected 14-day low: 0 → 136 units

Now drag **Launch campaign in (days)** to **3**. It flips back to:

> With +210 donations: Critical, still short in 7 days: too little or too late

Say: same campaign, three days later, shortage anyway. Units take four days to become usable.
Timing is the whole point. Drag the delay back to **0**.

Scroll to **BloodSight recommendation**:

| Target | 210 additional donations |
| --- | --- |
| Campaign window | 5 days |
| Latest effective launch | within 72 hours |
| Priority | High |
| Expected 14-day risk after campaign | Low |

And under "Why the model sees this": usage up 26% over the last two weeks, donations down 17% over
the same period, and a public holiday on Sat 03 Oct that typically drops donor turnout by about 55%.

Say: a recommendation nobody can act on is only a report. Click
**"Turn into a donor request for O-"**.

## 1:10 to 1:40. Tab 1, the request goes out

The page jumps to **Requests** with the form filled in. Read the caption:
"Filled in from the recommendation: 210 donations in 5 days." Blood type **O-**, target **210**,
five days of slots.

Optional, and it makes the patient screen much easier to read: in **Times a day**, leave only
**09:00** selected. Five slots instead of fifteen.

Point at the right column, **Who gets it**:

> **2,791 people match**
> Patients of Bloodlab Maastricht: 1,278
> Gave at this centre before: 1,513
> Expected bookings: about 251

And the line under it: "You see a count, not names. A name appears only when that person books a
slot."

Press **"Send to 2,791 people"**. The request card appears:

> Day 1 of 5. Asked **2,791**, Seen **1,897**, Booked **78**, Not this time **86**.
> 78 of 210 booked.

Say: these are the population's answers, simulated. Watch what a real account does on top of them.

## 1:40 to 2:10. Tab 2, the lab publishes and writes

Switch to tab 2, **Publish results**. Four figures: **212** reports, **205** ready, **3** where the
code does not match, **4** urgent values.

Point at the first held-back card: **BL-4907**, potassium 6.4 mmol/L, "Urgent: doctor is phoned
first". Its **Release** button is greyed out. Press **"Doctor has phoned"**. Release lights up. Say:
an app never delivers an urgent value first. The rule is in the data layer, not in the button.

Press **"Publish 205 to patients"**.

Go to **Notify patients**. Press the template button **"Lab closed on Friday"**. Leave "Who gets it"
on **All patients**. The card says **"2 people will get this"** and names them. Press
**"Send notification"**.

## 2:10 to 2:45. Tab 3, the patient

Switch to tab 3 and click **Results** in the sidebar. The report is there: "Blood test of Mon 14 Sep
· Bloodlab Maastricht · 18 values · 2 out of range". Two cards under "Outside the range the lab
printed":

- Ferritin (iron store): **18 ng/mL**, range printed by the lab: 30 to 300, Low
- LDL cholesterol: **3.9 mmol/L**, range printed by the lab: 0 to 3, High

Press **"Open Ferritin (iron store)"**. The chart shows this person's own three tests: **41, 33,
18**, with the lab minimum of 30 drawn across it. Right of it, under "Written by the AI":

> Ferritin is the protein that stores iron in the body. A ferritin result says how much iron is in
> store, not how much is in the blood right now. The lab marked this result as low: it is under the
> range the lab printed (30 to 300 ng/mL). It went down at every test: 41 on 12 Feb, 33 on 3 Jun, 18
> on 14 Sep. I cannot say why this value moved or what it means for you: that is a question for your
> doctor.

Point at the source line at the bottom: "source: report of 14 Sep, line 7", and at
**"Summary for my doctor"**, which downloads one page of plain text to take to the appointment.

Click **Needs** in the sidebar. The top card is the request you just sent:

> **Regional Blood Centre** needs **O-** · 2.1 km
> Shortage forecast · You gave here
> Why you: you are O-, you live 2.1 km away, you gave here on 3 Jul, you last gave 80 days ago.

Say: this is the part that usually goes wrong. Not a mass text to everyone. This person, for four
reasons they can read.

Press **"Book Tue 22 Sep · 09:00"**. The card turns into "Booked: Tue 22 Sep · 09:00 at Regional
Blood Centre". Point at **"Not this time"** before you click, and at the line under it: it costs
nothing and is never shown to the place.

## 2:45 to 3:00. Tab 1, the loop closes

Switch back to tab 1 and click **Notifications**:

> **New booking: Alex Jansen, Tue 22 Sep · 09:00**
> O- request REQ-3.

Click **Bookings**. One row is different from the rest:

| Slot | Name | Blood type | Note | Booked by |
| --- | --- | --- | --- | --- |
| Tue 22 Sep · 09:00 | **Alex J.** | O- | gave here 3 Jul | app account |

Booked is now **79**. Say: the centre asked 2,791 people and knows the name of the one who said yes.
Everybody else is still a number. Click **Outlook** to finish: the O- projection now carries a
second line, "Forecast, with 79 booked donations".

## The 60-second pitch

Blood banks run on a forecast that arrives too late and an appeal that goes to everybody. BloodSight
AI closes that gap in one loop. The blood centre sees, fourteen days out, that O- will fall under
its safety level in seven days: not because stock is low today, 184 units is five days of supply,
but because usage is up 26% and donations are down 17% and there is a holiday coming. The model
sizes the answer: 210 donations over five days, launched within 72 hours, because units take four
days to become usable. Delay it three days and the same campaign fails. Then the part that normally
breaks: the request has to reach people who can actually answer it. It goes to the lab's own
patients, to people who gave at that place before, and to people who live nearby, and every one of
them sees why they were asked. The lab is the other half. It publishes the day's results, holds back
urgent values until the doctor has phoned, and passes exactly one fact to the donor side: a blood
type. The centre sees counts. It learns a name at one moment only, when somebody books a slot. All
of it runs on synthetic data, and all of it runs in the three tabs you just watched.

## Three questions you will get

**Is this real patient data?**
No. Every number in the repository is synthetic. The stock history is generated by `forecast.py`,
the people a request reaches are a synthetic population of 120,000 rows in `store.py`, the lab batch
totals are constants, and the four full lab reports were written by hand. There is no real patient,
no real donor and no connection to any real system.

**Is the AI a large language model?**
No, and we do not claim it is. The forecast is a ridge regression: two per blood type, one for usage
and one for donations, trained on the last 42 days with day-of-week, trend and holiday features. Its
14-day backtest error is on the screen, 10% averaged over the eight types, 24% for O-, and the page
says why: the backtest hides exactly the window in which O- changed. The assistant and the value
explanations are rule-based. They are built from a fixed one-sentence description per value plus
that person's own numbers and trend, and they refuse three things by keyword: a diagnosis, a cause,
and any promise that the person can give blood. A language model would be a sensible next step for
the wording. It would not change the rules around it.

**What about privacy?**
Six rules, enforced in the data layer rather than written on a screen. Nobody is asked unless they
switched it on, and a pause or a per-place switch stops it. A place asking who it could reach gets a
count, never names. A place learns a name at one moment: when that person books a slot. "Not this
time" is stored as an input to a count and is never shown by name. A person is asked at most twice a
month. Urgent lab values are held back until the doctor has phoned, and the release button stays
disabled until that call is recorded. The lab passes one fact to the donor side, a blood type, and
the Donor link page lists what it never passes. The prototype itself has demo passwords in a public
repository and no production-grade security: it is a working model of the rules, not a system you
would put patient data into.
