"""Patient side: Results, Needs, Donations, Ask, Notifications, Me.

Screens retrieve this person's records. On an explicit AI request, a limited evidence packet
is sent to the configured OpenAI service. Centre staff still see names only through bookings.
The assistant is instructed to explain records without diagnosis or donation eligibility advice.
"""

from __future__ import annotations

import re
from datetime import date

import plotly.graph_objects as go
import streamlit as st

import store
import ui

PAGES = ["Results", "Needs", "Donations", "Ask", "Notifications", "Me"]

SUBTITLE = {
    "Results": "Your blood tests, as the lab printed them.",
    "Needs": "Places that need blood you can give.",
    "Donations": "What you gave and where it went.",
    "Ask": "Questions about your own results and donations.",
    "Notifications": "Everything the lab and the places sent you.",
    "Me": "Your switches, your details.",
}
URGENCY_RISK = {"Shortage forecast": "Critical", "This week": "Medium", "This month": "Low"}

VISIT_TEXT = ("Bring an ID. Eat and drink before you come. The centre does a short health check first "
              "and makes the final call.")
NOT_KNOWN = "Not known yet"   # blood type nobody has filled in; stored as None
SLOTS_PER_ROW = 4   # a day never shows more than four time buttons on one row
DAYS_SHOWN = 3      # the rest of the days go into the "More days" expander


# ------------------------------------------------------------------------ small helpers

def _day(iso: str) -> str:
    """2026-09-14 -> Mon 14 Sep."""
    d = date.fromisoformat(iso)
    return f"{d:%a} {d.day} {d:%b}"


def _short(iso: str) -> str:
    """2026-09-14 -> 14 Sep."""
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%b}"


def _slot(slot: str) -> str:
    """2026-09-22 16:30 -> Tue 22 Sep · 16:30."""
    day, _, time = slot.partition(" ")
    return f"{_day(day)} · {time}"


def _num(v: float) -> str:
    return f"{v:g}"


def _flag_chip(flag: str) -> str:
    """Out of range is amber, in range is green. Color never travels without an icon and a label."""
    bg, fg, icon = {"Low": ("#fdf3d9", "#b97d00", "🟡"), "High": ("#fdf3d9", "#b97d00", "🟡")}.get(
        flag, ("#e6f4e6", "#0a7d0a", "🟢"))
    return f'<span class="bs-chip" style="background:{bg};color:{fg}">{icon} {flag}</span>'


def _close_value() -> None:
    """Leave the opened value and go back to the list of results."""
    st.session_state.pop("open_value", None)
    st.session_state.pop("_value_open", None)


def _goto(page: str) -> None:
    """Jump to another page. The nav radio already exists in this run, so the move is staged for the next."""
    st.session_state["_goto"] = page
    st.rerun()


def _donor_on(user: dict) -> bool:
    sw = user.get("switches", {})
    return bool(sw.get("nearby") or sw.get("gave_before"))


# ------------------------------------------------------------------ report summary


def _doctor_summary(user: dict, report: dict) -> str:
    """One page of plain text to take to a doctor: out-of-range values, ranges, trend, dates."""
    out = [v for v in report["values"] if v["flag"] != "In range"]
    lines = ["BloodSight AI: summary for my doctor", "",
             f"Name: {user['name']}", f"Lab code: {user.get('lab_code', '')}",
             f"Report: blood test of {_day(report['date'])}, {report['lab']}",
             f"Printed: {_day(store.today().isoformat())}", "",
             "Values outside the range printed by the lab"]
    if not out:
        lines.append("- none: every value was inside the printed range.")
    for v in out:
        hist = store.value_history(user["username"], v["key"])
        lines.append(f"- {v['name']}: {_num(v['value'])} {v['unit']} "
                     f"(range printed by the lab: {_num(v['low'])} to {_num(v['high'])}). Lab flag: {v['flag']}.")
        if len(hist) > 1:
            lines.append("  Earlier tests: "
                         + ", ".join(f"{_num(h['value'])} on {_short(h['date'])}" for h in hist) + ".")
    lines += ["", f"All other values were inside the printed range ({len(report['values']) - len(out)} values).",
              f"Blood type from this test: {report['blood_type']}"]
    d = store.donations(user["username"])
    if d["total"]:
        lines.append(f"Donations on record: {d['total']} at {d['places']} places. "
                     f"Last donation: {_day(d['history'][0]['date'])}.")
    lines += ["", "This summary was put together by a prototype from this person's own lab reports.",
              "It contains no diagnosis and no cause."]
    return "\n".join(lines)


# -------------------------------------------------------------------------------- results

def _value_cards(values: list[dict], report: dict, prefix: str) -> None:
    """Value cards in a grid, each with a button that opens the value."""
    for row_start in range(0, len(values), 3):
        row = values[row_start:row_start + 3]
        for col, v in zip(st.columns(3), row):
            with col:
                st.markdown(f'<div class="bs-card"><div class="units" style="margin:0 0 6px">{v["name"]}</div>'
                            f'<div class="bt">{_num(v["value"])} <span style="font-size:.9rem;font-weight:400;'
                            f'color:{ui.INK_2}">{v["unit"]}</span></div>'
                            f'<div class="sub" style="margin:6px 0 8px">Range printed by the lab: '
                            f'{_num(v["low"])} to {_num(v["high"])}</div>{_flag_chip(v["flag"])}</div>',
                            unsafe_allow_html=True)
                if st.button(f"Open {v['name']}", key=f"{prefix}_{report['id']}_{v['key']}",
                             use_container_width=True):
                    _close_value()
                    st.session_state["open_value"] = (report["id"], v["key"])
                    st.rerun()


def _trend_chart(hist: list[dict], v: dict) -> None:
    """The person's own tests with the lab's minimum and maximum. The axis follows the values, so a far-away
    bound (ferritin: a maximum of 300 against results near 20) is named in a caption instead of flattening
    the line."""
    vals = [h["value"] for h in hist]
    lo_d, hi_d = min(vals), max(vals)
    span = max(hi_d - lo_d, abs(hi_d) * 0.2, 1e-9) or 1
    near = [(level, label) for level, label in ((v["low"], "Lab minimum"), (v["high"], "Lab maximum"))
            if lo_d - 3 * span <= level <= hi_d + 3 * span]
    lo = min([lo_d - 0.5 * span] + [level - 0.15 * span for level, _ in near])
    hi = max([hi_d + 0.5 * span] + [level + 0.15 * span for level, _ in near])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[_short(h["date"]) for h in hist], y=vals, mode="lines+markers",
                             name="Your result", line=dict(color=ui.BLUE, width=2),
                             marker=dict(size=9, color=ui.BLUE), hovertemplate="%{y:g} " + v["unit"]))
    for level, label in near:
        fig.add_shape(type="line", xref="paper", x0=0, x1=1, y0=level, y1=level,
                      line=dict(color="#d03b3b", width=1.5, dash="dot"))
        fig.add_annotation(xref="paper", x=0.01, y=level, text=f"{label} · {_num(level)}", showarrow=False,
                           xanchor="left", yanchor="bottom", font=dict(size=11, color=ui.INK_2))
    fig.update_layout(title=dict(text=f"{v['name']}: your tests", font=dict(size=15, color=ui.INK)),
                      height=300, margin=dict(l=10, r=10, t=50, b=10), showlegend=False,
                      plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb", font=dict(color=ui.INK_2),
                      yaxis=dict(title=v["unit"], range=[lo, hi], gridcolor=ui.GRID, zeroline=False),
                      xaxis=dict(showgrid=False, linecolor=ui.AXIS))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    off = [f"{label.lower()} of {_num(level)}" for level, label in ((v["low"], "Lab minimum"), (v["high"], "Lab maximum"))
           if (level, label) not in near]
    st.caption(f"Range printed by the lab: {_num(v['low'])} to {_num(v['high'])} {v['unit']}."
               + (f" The {' and the '.join(off)} {'falls' if len(off) == 1 else 'fall'} outside this chart."
                  if off else ""))


def _value_page(user: dict, report: dict, key: str) -> None:
    """One recorded value, its supplied range and an optional live AI explanation."""
    v = next((x for x in report["values"] if x["key"] == key), None)
    if v is None:
        _close_value()
        st.rerun()
    back, _ = st.columns([1, 4])
    fired = back.button("Back to results", key="back_to_results", type="primary", use_container_width=True)
    if fired:
        _close_value()
        st.rerun()

    st.markdown(f"### {v['name']}")
    st.markdown(f'<div class="bs-card"><div class="bt" style="font-size:2.1rem">{_num(v["value"])} '
                f'<span style="font-size:1rem;font-weight:400;color:{ui.INK_2}">{v["unit"]}</span> '
                f'{_flag_chip(v["flag"])}</div>'
                f'<div class="sub">Range printed by the lab: {_num(v["low"])} to {_num(v["high"])} {v["unit"]}'
                f'</div></div>', unsafe_allow_html=True)

    hist = store.value_history(user["username"], key)
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        _trend_chart(hist, v)
    with right:
        st.markdown("##### AI explanation")
        from views.ai_panel import explain_value
        explain_value(user, report, v)
    st.caption(f"source: report of {_short(report['date'])}, line {v['line']}")
    fired = st.download_button("Summary for my doctor", _doctor_summary(user, report), type="primary",
                               file_name=f"bloodsight-summary-{report['date']}.txt", mime="text/plain",
                               key=f"dl_{report['id']}_{key}") or fired
    # A rerun that none of this value's own controls caused came from somewhere else on the screen
    # (the report picker, the sidebar): close the value rather than leave it standing over the list.
    if st.session_state.get("_value_open") == (report["id"], key) and not fired:
        _close_value()
        st.rerun()
    st.session_state["_value_open"] = (report["id"], key)


def _results(user: dict) -> None:
    if not user.get("switches", {}).get("results"):
        st.info("Your results are switched off. Turn on 'Show me my lab results' under Me to see them here.")
        return
    reports = store.reports_for(user["username"])
    if not reports:
        st.info("Nothing published yet. Your blood test appears here as soon as the lab publishes it.")
        return

    # An opened value sits on top of the list, never instead of it. Clicking "Results" in the sidebar
    # while Results is already selected sends nothing to the server, so a value that replaced the list
    # would be a dead end: here the list is always underneath.
    opened = st.session_state.get("open_value")
    if opened and any(r["id"] == opened[0] for r in reports):
        _value_page(user, next(r for r in reports if r["id"] == opened[0]), opened[1])
        st.divider()

    picked = reports[0]
    if len(reports) > 1:
        labels = {f"Blood test of {_day(r['date'])}": r for r in reports}
        picked = labels[st.selectbox("Report", list(labels), index=0)]
    out = [v for v in picked["values"] if v["flag"] != "In range"]
    ok = [v for v in picked["values"] if v["flag"] == "In range"]
    st.markdown(f"#### Blood test of {_day(picked['date'])} · {picked['lab']} · {len(picked['values'])} values "
                f"· {len(out)} out of range")

    if out:
        st.caption("Outside the range the lab printed")
        _value_cards(out, picked, "out")
    else:
        st.markdown('<div class="bs-alert ok"><h4>🟢 Every value is inside the range the lab printed</h4>'
                    '<p>Nothing in this report is flagged.</p></div>', unsafe_allow_html=True)
    if ok:
        with st.expander(f"{len(ok)} more values, all in range" if out else f"{len(ok)} values, all in range"):
            _value_cards(ok, picked, "in")
    st.caption(f"Blood type from this test: {picked['blood_type']} · Source: {picked.get('source', 'Synthetic demo')}")

    # Bridge to the donor side. Only for people who switched the donor part on, and only if something is open.
    needs = store.needs_for(user["username"]) if _donor_on(user) else []
    needs = [n for n in needs if not n["declined"]]
    if needs:
        # Name the type only when every open need asks for the same one: two different types are "blood".
        kinds = {n["blood_type"] for n in needs}
        what = next(iter(kinds)) if len(kinds) == 1 else "blood"
        if what == store.ANY_TYPE:
            what = "plasma, which any blood type can give"
        one = len(needs) == 1
        st.markdown("")
        st.markdown(f'<div class="bs-card"><b>{len(needs)} {"place" if one else "places"} near you '
                    f'{"needs" if one else "need"} {what}</b>'
                    f'<div class="units">You switched this on. Giving blood is up to you, every time.'
                    f'</div></div>', unsafe_allow_html=True)
        if st.button("See what is needed", key="bridge_to_needs", type="primary"):
            _goto("Needs")


# ---------------------------------------------------------------------------------- needs

def _by_day(slots: list[str]) -> list[tuple[str, list[str]]]:
    """['2026-09-22 09:00', ...] -> [('2026-09-22', ['09:00', '13:00', '16:30']), ...], days in order."""
    days: dict[str, list[str]] = {}
    for slot in sorted(slots):
        day, _, time = slot.partition(" ")
        days.setdefault(day, []).append(time)
    return list(days.items())


def _day_row(user: dict, n: dict, day: str, times: list[str]) -> None:
    """One day of a request: the day on the left, that day's times as buttons next to it."""
    for start in range(0, len(times), SLOTS_PER_ROW):
        cols = st.columns([1.5] + [1] * SLOTS_PER_ROW)
        cols[0].markdown(f'<div style="padding-top:7px;font-weight:600;color:{ui.INK}">'
                         f'{_day(day) if start == 0 else "&nbsp;"}</div>', unsafe_allow_html=True)
        for col, time in zip(cols[1:], times[start:start + SLOTS_PER_ROW]):
            if col.button(time, key=f"book_{n['id']}_{day}_{time}", type="primary",
                          use_container_width=True):
                store.book(user["username"], n["id"], f"{day} {time}")
                st.rerun()


def _need_card(user: dict, n: dict) -> None:
    dist = f"{_num(n['distance_km'])} km" if n["distance_km"] is not None else "nearby"
    gave = '<span class="bs-chip" style="background:#eef4fc;color:#2a78d6">You gave here</span>' if n["gave_here"] else ""
    # One bordered container per need, so the buttons visibly belong to the card they act on.
    with st.container(border=True):
        st.markdown(f'<div class="bs-card" style="border:0;padding:0;background:transparent">'
                    f'<div class="bt">{n["place_name"]}</div>'
                    f'<div class="units">needs <b>{n["blood_type"]}</b> · {dist}</div>'
                    f'{ui.chip(URGENCY_RISK.get(n["urgency"], "Low"), n["urgency"])} {gave}'
                    f'<div class="sub">Why you: {", ".join(n["reasons"])}.</div></div>', unsafe_allow_html=True)

        booking = n["my_booking"]
        if booking:
            st.success(f"Booked: {_slot(booking['slot'])} at {n['place_name']}")
            if st.button("Cancel booking", key=f"cancel_{booking['id']}"):
                store.cancel_booking(user["username"], booking["id"])
                st.rerun()
        else:
            st.caption("Pick a time")
            days = _by_day(n["slots"])
            for day, times in days[:DAYS_SHOWN]:
                _day_row(user, n, day, times)
            if len(days) > DAYS_SHOWN:
                with st.expander("More days"):
                    for day, times in days[DAYS_SHOWN:]:
                        _day_row(user, n, day, times)
            cols = st.columns([1.5] + [1] * SLOTS_PER_ROW)
            if cols[1].button("Not this time", key=f"decline_{n['id']}", use_container_width=True):
                store.decline(user["username"], n["id"])
                st.rerun()
            st.caption("'Not this time' costs nothing and is never shown to the place.")
        with st.expander("What happens at the visit"):
            st.markdown(n["message"])
            st.markdown(VISIT_TEXT)
            st.caption("The app never promises that you can give: the centre decides at the visit.")
    st.markdown("")


def _needs(user: dict) -> None:
    if not _donor_on(user):
        st.info("The donor part is switched off, so nothing is shown here. Turn on 'Tell me when a place nearby "
                "needs my blood type' or 'Tell places I gave to before' under Me. Results only is a valid way to "
                "use the app.")
        return
    if user.get("paused"):
        st.warning("All requests are paused. Nothing will be shown or sent until you turn the pause off.")

    items = store.needs_for(user["username"])
    hidden = [n for n in items if n["declined"] and not n["my_booking"]]
    items = [n for n in items if not n["declined"] or n["my_booking"]]

    choice = st.radio("Show", ["All", "My type", "Places I gave to"], horizontal=True, key="needs_filter")
    if choice == "My type":
        items = [n for n in items if n["blood_type"] == user.get("blood_type")]
    elif choice == "Places I gave to":
        items = [n for n in items if n["gave_here"]]

    if not items:
        st.info("Nothing within reach needs you right now." if not user.get("paused")
                else "Nothing is shown while requests are paused.")
    for n in items:
        _need_card(user, n)
    if hidden:
        st.caption(f"{len(hidden)} request hidden: you said not this time.")

    st.divider()
    st.caption("You get at most two request notifications a month. Open needs near you stay listed here.")
    paused = st.toggle("Pause all requests", value=bool(user.get("paused")), key="pause_needs")
    if paused != bool(user.get("paused")):
        store.update_user(user["username"], paused=paused)
        st.rerun()


# ------------------------------------------------------------------------------ donations

def _donations(user: dict) -> None:
    d = store.donations(user["username"])
    bookings = store.my_bookings(user["username"])
    st.markdown(f"#### {d['total']} donation{'s' if d['total'] != 1 else ''} · {d['places']} places")

    st.markdown("##### Booked")
    if bookings:
        # store.my_bookings returns only slots that are still booked, so a slot the centre cancelled
        # is gone from this list on the next run. Nothing here is kept in session state.
        for b in bookings:
            with st.container(border=True):
                st.markdown(f'<div class="bs-card" style="border:0;padding:0;background:transparent">'
                            f'<b>{_slot(b["slot"])}</b>'
                            f'<div class="units">{b["place_name"]}</div>'
                            f'<div class="sub">{VISIT_TEXT}</div></div>', unsafe_allow_html=True)
                cols = st.columns([1, 2])
                if cols[0].button("Cancel booking", key=f"dcancel_{b['id']}", use_container_width=True):
                    store.cancel_booking(user["username"], b["id"])
                    st.rerun()
    else:
        st.caption("No slot booked.")
    st.caption("Next possible date: set by the donor centre.")

    st.markdown("##### Where it went")
    if d["history"]:
        for h in d["history"]:
            st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{_day(h["date"])} · {h["kind"]}</b>'
                        f'<div class="units">{h["place_name"]}</div>'
                        f'<div class="sub">{h["used"]}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("No donations on record yet.")

    places = {h["place"]: h["place_name"] for h in d["history"]}
    if places:
        st.markdown("##### Places you gave to")
        for key, name in places.items():
            on = user.get("places", {}).get(key, True)
            new = st.toggle(f"{name}: may ask me", value=bool(on), key=f"place_{key}")
            if new != bool(on):
                store.update_user(user["username"], places={key: new})
                st.rerun()


# ------------------------------------------------------------------------------------ me

def _me(user: dict) -> None:
    sw = user.get("switches", {})
    st.markdown("##### What may the app do?")
    fields = [("results", "Show me my lab results"),
              ("nearby", "Tell me when a place nearby needs my blood type"),
              ("gave_before", "Tell places I gave to before when I am allowed to give again")]
    for key, label in fields:
        new = st.toggle(label, value=bool(sw.get(key)), key=f"sw_{key}")
        if new != bool(sw.get(key)):
            store.update_user(user["username"], switches={key: new})
            st.rerun()
    st.caption("Each switch can be turned off. Results only is a valid way to use the app: with both donor "
               "switches off, Needs stays empty and says so.")

    st.divider()
    paused = st.toggle("Pause all requests", value=bool(user.get("paused")), key="pause_me")
    if paused != bool(user.get("paused")):
        store.update_user(user["username"], paused=paused)
        st.rerun()
    st.caption("You are asked at most twice a month, pause or no pause.")

    st.divider()
    st.markdown("##### Your details")
    with st.form("me_details"):
        c1, c2 = st.columns(2)
        postcode = c1.text_input("Postcode", value=user.get("postcode", ""))
        # "Not known yet" is the first option and the only pre-selection for a person whose type is
        # unknown: a blood type nobody gave must never be pre-filled, it decides who gets asked.
        current = user.get("blood_type")
        options = [NOT_KNOWN] + store.BLOOD_TYPES
        blood_type = c2.selectbox("Blood type", options,
                                  index=options.index(current) if current in options else 0)
        st.caption("Your blood type comes from your lab result. Change it only if the lab has it wrong."
                   if current else "Not known yet. Your lab result fills it in when the lab publishes.")
        if st.form_submit_button("Save", type="primary"):
            store.update_user(user["username"], postcode=postcode.strip(),
                              blood_type=None if blood_type == NOT_KNOWN else blood_type)
            st.rerun()
    st.markdown(f'<div class="bs-card"><div class="units">Lab code <b>{user.get("lab_code", "")}</b><br>'
                f'Patient of {store.LAB_NAME}</div></div>', unsafe_allow_html=True)


# -------------------------------------------------------------------------------- router

def render(user: dict) -> None:
    goto = st.session_state.pop("_goto", None)
    if goto in PAGES:
        st.session_state["nav"] = goto  # staged before the nav radio is built, so Streamlit allows the write
    page = ui.sidebar(user, PAGES)
    if st.session_state.get("_last_page") != page:
        st.session_state["_last_page"] = page
        _close_value()
    ui.header(page, SUBTITLE[page])
    if page == "Results":
        _results(user)
    elif page == "Needs":
        _needs(user)
    elif page == "Donations":
        _donations(user)
    elif page == "Ask":
        from views.ai_panel import chat
        chat(user)
    elif page == "Notifications":
        ui.notification_list(user["username"], "Nothing yet. The lab and the places write here.")
    else:
        _me(user)
