# BloodSight AI

Hackathon prototype: a dashboard that forecasts blood-bank inventory 14 days ahead, flags a
shortage before it happens, recommends a donor campaign, and lets the user test the campaign
in a what-if simulator. All data is synthetic.

## Run

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\streamlit run app.py
```

`python forecast.py 2026-09-21` regenerates `data.csv` ending on the given date (default: today).
The demo numbers below are for the dataset ending 2026-09-21; a different end date shifts the
weekday alignment and the numbers move slightly, so regenerate once and rehearse on that file.

## Login

Two roles, demo accounts only (hardcoded in `auth.py`, shown on the login page, no real security):

| Username | Password | Role |
| --- | --- | --- |
| lab | lab123 | Lab / doctor: full forecasting dashboard, can launch and end donor campaigns |
| patient | patient123 | Patient, blood type O-: own supply outlook, compatible supply, donation pledge |
| patient2 | patient123 | Patient, blood type A+: the "nothing needed" case |

A login lasts for the browser tab; a page refresh returns to the login page. Campaigns and pledges
are kept in `state.json`. Delete that file to reset the demo.

Two-tab demo: tab 1 as lab, launch the O- campaign. Tab 2 as patient, see the appeal and pledge.
Back in tab 1, click any control (or switch blood type and back) and the pledge count shows 1 of 210.

## Files

- `forecast.py`: synthetic data generator, ridge-regression forecast, risk rules, campaign sizing, backtest.
- `app.py`: Streamlit entry point and the lab / doctor dashboard.
- `auth.py`: demo login, campaign and pledge state.
- `patient.py`: patient view.
- `data.csv`: 180 days x 8 blood types (donations, usage, closing inventory).

## Demo path (about 90 seconds)

1. Cards: seven of eight types look fine today. O- has 184 units, five days of supply, no shortage.
2. Alert + chart: the forecast crosses the safety threshold (100 units) in 7 days.
3. "Why the model sees this": usage up 26 %, donations down 17 %, a public holiday inside the horizon.
4. Recommendation: 210 additional donations over 5 days, launch within 72 hours.
5. What-if slider: +100 still ends in a shortage, +150 avoids it, +210 restores the buffer.
6. Delay slider: keep +210 but launch 3 days later and the shortage comes back. Timing is the point.
7. Optional: open "Behind the forecast" for the model description and the backtest error.

## How the model works

Per blood type, two ridge regressions (usage, donations) on the last 42 days with day-of-week,
trend and public-holiday features. Projected inventory = current inventory + predicted donations
- predicted usage. Thresholds are days of supply at the 90-day average usage: under 3 days is
critical, under 5 days is medium. Campaign units become usable 4 days after launch (outreach,
then testing and processing). The recommended size is the smallest campaign, found by simulation,
that avoids the shortage and ends the 14 days above the warning level.

Not modelled: unit expiry (42-day shelf life), cross-type substitution, transfers between centres.
