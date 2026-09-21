"""Donor side: Results, Needs, Donations, Ask, Notifications, Me.

Screens retrieve this person's records. On an explicit AI request, a limited evidence packet
is sent to the configured AI provider. Centre staff still see names only through bookings.
The assistant is instructed to explain records without diagnosis or donation eligibility advice.
"""

from __future__ import annotations

import re
from datetime import date

import plotly.graph_objects as go
import streamlit as st

import store
import ui

PAGES = ["Results", "Needs", "Donations", "Ask", "Notifications", "Me", "SMS test"]

SUBTITLE = {
    "Results": "Your lab reports",
    "Needs": "Open requests near you",
    "Donations": "Your donations and bookings",
    "Ask": "Your results, donations and needs",
    "Notifications": "From the lab and the places",
    "Me": "Switches and details",
    "SMS test": "Send a test message to your own phone.",
}
INK, INK_MUTED, BORDER = "#111827", "#6b7280", "#e5e4df"
OK_GREEN, WARN_AMBER = "#15803d", "#b45309"
CSS = """<style>
.bs-h{font-size:15px;font-weight:600;color:#111827;margin:18px 0 8px}
.bs-c{font-size:13px;color:#111827;padding:7px 0;border-bottom:1px solid #e5e4df;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bs-r{text-align:right;font-variant-numeric:tabular-nums}
.bs-hd{font-size:11.5px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:.04em;padding:0 0 6px;border-bottom:1px solid #e5e4df}
.bs-sep{font-size:12.5px;font-weight:600;color:#6b7280;padding:16px 0 4px;border-top:1px solid #e5e4df;margin-top:2px}
.bs-note{font-size:12.5px;color:#6b7280}
.bs-line{font-size:13px;color:#4b5563}
div[class*="st-key-rowbtn_"]{border-bottom:1px solid #e5e4df}
div[class*="st-key-rowbtn_"] button{border:0 !important;background:transparent !important;color:#6b7280 !important;box-shadow:none !important;padding:0 !important;height:31px !important;min-height:31px !important;justify-content:flex-start !important}
div[class*="st-key-rowbtn_"] button:hover{color:#c8102e !important;text-decoration:underline}
div[class*="st-key-rowbtn_"] button p{font-size:12.5px !important;font-weight:500 !important}
div[class*="st-key-book_"] button{height:32px !important;min-height:32px !important;width:66px !important;min-width:66px !important;padding:0 !important}
div[class*="st-key-book_"] button p{font-size:13px !important}
div[class*="st-key-decline_"] button,div[class*="st-key-quiet_"] button{border:0 !important;background:transparent !important;color:#6b7280 !important;box-shadow:none !important;padding:0 !important;height:32px !important;min-height:32px !important;justify-content:flex-start !important}
div[class*="st-key-decline_"] button:hover,div[class*="st-key-quiet_"] button:hover{color:#c8102e !important;text-decoration:underline}
div[class*="st-key-decline_"] button p,div[class*="st-key-quiet_"] button p{font-size:13px !important}
div[class*="st-key-sug_"] button{max-width:100% !important;height:auto !important;min-height:36px !important;white-space:normal !important;padding:8px 14px !important}
div[class*="st-key-sug_"] button p{font-size:13px !important;white-space:normal !important;line-height:1.35 !important}
</style>"""
URGENCY_RISK = {"Shortage forecast": "Critical", "This week": "Medium", "This month": "Low"}

SUGGESTIONS = ["Why is my ferritin low?", "What does my ferritin mean?", "What is my haemoglobin?",
               "Can I give blood?", "Where did my blood go?", "What needs my blood near me?",
               "Do I need a doctor?"]

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
    """Out of range is amber, in range is green: a dot plus plain coloured text, never a pill."""
    fg = WARN_AMBER if flag in ("Low", "High") else OK_GREEN
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;'
            f'color:{fg}"><span style="width:6px;height:6px;border-radius:50%;background:{fg};'
            f'display:inline-block"></span>{flag}</span>')


def _tag(text: str, color: str = INK_MUTED) -> str:
    """A plain small tag such as 'You gave here': a dot and text, no box."""
    return (f'<span style="display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;'
            f'color:{color}"><span style="width:6px;height:6px;border-radius:50%;background:{color};'
            f'display:inline-block"></span>{text}</span>')


def _h(text: str) -> None:
    st.markdown(f'<div class="bs-h">{text}</div>', unsafe_allow_html=True)


def _close_value() -> None:
    """Leave the opened value: the list of results is underneath it."""
    st.session_state.pop("open_value", None)


def _goto(page: str) -> None:
    """Jump to another page. The nav radio already exists in this run, so the move is staged for the next."""
    st.session_state["_goto"] = page
    st.rerun()


def _donor_on(user: dict) -> bool:
    sw = user.get("switches", {})
    return bool(sw.get("nearby") or sw.get("gave_before"))


def _link_lab_code(user: dict, where: str) -> None:
    """Compact panel for a donor who signed up without a lab code. Shown on Results and under Me.

    The store raises ValueError with the reason a code is refused, so the message the donor reads is the
    store's own wording and never a rewritten one.
    """
    _h("Link your lab results")
    st.markdown('<div class="bs-note">Your lab code is printed on your lab letter.</div>',
                unsafe_allow_html=True)
    left, right = st.columns([2.2, 1], vertical_alignment="bottom")
    code = left.text_input("Lab code", placeholder="BL-4821", key=f"labcode_{where}")
    if right.button("Link", key=f"labcode_btn_{where}", type="primary"):
        try:
            store.link_lab_code(user["username"], code)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.rerun()


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
    lines += ["", "This summary was put together from this person's own lab reports.",
              "It contains no diagnosis and no cause."]
    return "\n".join(lines)


# -------------------------------------------------------------------------------- results

ROW_COLS = [3.4, 1.7, 2.0, 1.3, 1.0]


def _table_head() -> None:
    cols = st.columns(ROW_COLS, gap="small")
    for col, (label, cls) in zip(cols, [("Test", "bs-hd"), ("Result", "bs-hd bs-r"),
                                        ("Reference range", "bs-hd bs-r"), ("Flag", "bs-hd"), ("", "bs-hd")]):
        col.markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)


def _value_row(v: dict, report: dict, prefix: str) -> None:
    """One line of the report, as a lab prints it: name, result, range, flag, and a quiet way in."""
    cols = st.columns(ROW_COLS, gap="small", vertical_alignment="center")
    cols[0].markdown(f'<div class="bs-c">{v["name"]}</div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="bs-c bs-r">{_num(v["value"])} '
                     f'<span style="color:{INK_MUTED}">{v["unit"]}</span></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="bs-c bs-r">{_num(v["low"])} to {_num(v["high"])}</div>',
                     unsafe_allow_html=True)
    cols[3].markdown(f'<div class="bs-c">{_flag_chip(v["flag"])}</div>', unsafe_allow_html=True)
    if cols[4].button("Details", key=f"rowbtn_{prefix}_{report['id']}_{v['key']}"):
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
    fig.update_layout(title=None,
                      height=220, margin=dict(l=10, r=10, t=14, b=10), showlegend=False,
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
    if st.button("Back to results", key="quiet_back_to_results"):
        _close_value()
        st.rerun()

    hist = store.value_history(user["username"], key)
    st.markdown(f'<div style="font-size:20px;font-weight:600;color:{INK};margin:2px 0 2px">{v["name"]}</div>'
                f'<div style="display:flex;align-items:baseline;gap:14px;flex-wrap:wrap">'
                f'<span style="font-size:24px;font-weight:600;color:{INK}">{_num(v["value"])} '
                f'<span style="font-size:13px;font-weight:400;color:{INK_MUTED}">{v["unit"]}</span></span>'
                f'{_flag_chip(v["flag"])}'
                f'<span style="font-size:12.5px;color:{INK_MUTED}">Reference range '
                f'{_num(v["low"])} to {_num(v["high"])} {v["unit"]}</span></div>', unsafe_allow_html=True)

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        _trend_chart(hist, v)
    with right:
        _h("About this value")
        from views.ai_panel import explain_value
        explain_value(user, report, v)
    st.caption(f"Source: report of {_short(report['date'])}, line {v['line']}")
    st.download_button("Summary for my doctor", _doctor_summary(user, report), type="primary",
                       file_name=f"bloodsight-summary-{report['date']}.txt", mime="text/plain",
                       key=f"dl_{report['id']}_{key}")


def _results(user: dict) -> None:
    if not user.get("switches", {}).get("results"):
        st.info("Your results are switched off. Turn on 'Show me my lab results' under Me to see them here.")
        return
    if not user.get("lab_code"):
        # Signed up without a lab code: nothing can be shown until the account is tied to a lab record.
        _link_lab_code(user, "results")
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
    _h(f"Blood test of {_day(picked['date'])} · {picked['lab']} · {len(picked['values'])} values "
       f"· {len(out)} out of range")

    # Every value of the report is on the page: out of range first, then all in-range values. Nothing is
    # folded away, so the count in the heading always matches what is visible.
    _table_head()
    for v in out:
        _value_row(v, picked, "out")
    if ok:
        if out:
            st.markdown(f'<div class="bs-sep">In range ({len(ok)})</div>', unsafe_allow_html=True)
        for v in ok:
            _value_row(v, picked, "in")
    st.markdown(f'<div class="bs-note" style="margin-top:10px">Blood type from this test: '
                f'<b style="color:{INK}">{picked["blood_type"]}</b></div>', unsafe_allow_html=True)
    st.caption(f"Source: {picked.get('source', 'Synthetic demo')}")

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
        st.markdown(f'<div class="bs-card" style="padding:16px 18px"><b>{len(needs)} '
                    f'{"place" if one else "places"} near you '
                    f'{"needs" if one else "need"} {what}</b></div>', unsafe_allow_html=True)
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
        cols = st.columns([1.6] + [0.8] * SLOTS_PER_ROW + [3], gap="small",
                          vertical_alignment="center")
        cols[0].markdown(f'<div style="font-size:13px;font-weight:600;color:{INK}">'
                         f'{_day(day) if start == 0 else "&nbsp;"}</div>', unsafe_allow_html=True)
        for col, time in zip(cols[1:], times[start:start + SLOTS_PER_ROW]):
            if col.button(time, key=f"book_{n['id']}_{day}_{time}"):
                store.book(user["username"], n["id"], f"{day} {time}")
                st.rerun()


def _need_card(user: dict, n: dict) -> None:
    dist = f"{_num(n['distance_km'])} km" if n["distance_km"] is not None else "nearby"
    gave = _tag("You gave here") if n["gave_here"] else ""
    # One bordered container per need, so the buttons visibly belong to the card they act on.
    with st.container(border=True):
        left, right = st.columns([3.2, 1], vertical_alignment="top")
        left.markdown(f'<div style="font-size:15px;font-weight:600;color:{INK}">{n["place_name"]}</div>'
                      f'<div style="font-size:13px;color:#4b5563;margin-top:2px">needs '
                      f'<b style="color:{INK}">{n["blood_type"]}</b> · {dist}</div>'
                      f'<div class="bs-note" style="margin-top:4px">{n["message"]} '
                      f'Why you: {", ".join(n["reasons"])}.</div>', unsafe_allow_html=True)
        right.markdown(f'<div style="display:flex;justify-content:flex-end;align-items:center;gap:10px;'
                       f'flex-wrap:wrap">'
                       f'{ui.chip(URGENCY_RISK.get(n["urgency"], "Low"), n["urgency"])}{gave}</div>',
                       unsafe_allow_html=True)

        booking = n["my_booking"]
        if booking:
            st.markdown(f'<div style="font-size:13px;color:{INK};margin:10px 0 2px">'
                        f'{_tag("Booked", OK_GREEN)} &nbsp;{_slot(booking["slot"])}</div>',
                        unsafe_allow_html=True)
            if st.button("Cancel booking", key=f"quiet_cancel_{booking['id']}"):
                store.cancel_booking(user["username"], booking["id"])
                st.rerun()
        else:
            days = _by_day(n["slots"])
            for day, times in days[:DAYS_SHOWN]:
                _day_row(user, n, day, times)
            if len(days) > DAYS_SHOWN:
                with st.expander("More days"):
                    for day, times in days[DAYS_SHOWN:]:
                        _day_row(user, n, day, times)
            cols = st.columns([1.6, 3], gap="small")
            if cols[0].button("Not this time", key=f"decline_{n['id']}"):
                store.decline(user["username"], n["id"])
                st.rerun()
        st.markdown(f'<div class="bs-note" style="margin-top:6px">{VISIT_TEXT} '
                    f'The centre decides at the visit.</div>', unsafe_allow_html=True)
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
    st.caption("At most two request notifications a month.")
    paused = st.toggle("Pause all requests", value=bool(user.get("paused")), key="pause_needs")
    if paused != bool(user.get("paused")):
        store.update_user(user["username"], paused=paused)
        st.rerun()


# ------------------------------------------------------------------------------ donations

def _donations(user: dict) -> None:
    d = store.donations(user["username"])
    bookings = store.my_bookings(user["username"])
    _h(f"{d['total']} donation{'s' if d['total'] != 1 else ''} · {d['places']} places")

    _h("Booked")
    if bookings:
        # Read straight from store.my_bookings on every run, which returns only slots that still
        # stand: nothing here is cached, so a slot the store cancelled is gone from this list.
        for b in bookings:
            with st.container(border=True):
                st.markdown(f'<div style="font-size:14px;font-weight:600;color:{INK}">{_slot(b["slot"])}</div>'
                            f'<div style="font-size:13px;color:#4b5563;margin-top:2px">{b["place_name"]}</div>'
                            f'<div class="bs-note" style="margin-top:4px">{VISIT_TEXT}</div>',
                            unsafe_allow_html=True)
                if st.button("Cancel booking", key=f"quiet_dcancel_{b['id']}"):
                    store.cancel_booking(user["username"], b["id"])
                    st.rerun()
    else:
        st.caption("No slot booked.")
    st.caption("Next possible date: set by the donor centre.")

    _h("Where it went")
    if d["history"]:
        for h in d["history"]:
            st.markdown(f'<div style="padding:8px 0;border-bottom:1px solid {BORDER}">'
                        f'<div style="font-size:13px;font-weight:600;color:{INK}">{_day(h["date"])} · '
                        f'{h["kind"]} · {h["place_name"]}</div>'
                        f'<div class="bs-note">{h["used"]}</div></div>', unsafe_allow_html=True)
    else:
        st.caption("No donations on record yet.")

    places = {h["place"]: h["place_name"] for h in d["history"]}
    if places:
        _h("Places you gave to")
        for key, name in places.items():
            on = user.get("places", {}).get(key, True)
            new = st.toggle(f"{name}: may ask me", value=bool(on), key=f"place_{key}")
            if new != bool(on):
                store.update_user(user["username"], places={key: new})
                st.rerun()


# ------------------------------------------------------------------------------------ me

def _me(user: dict) -> None:
    sw = user.get("switches", {})
    _h("What may the app do?")
    fields = [("results", "Show me my lab results"),
              ("nearby", "Tell me when a place nearby needs my blood type"),
              ("gave_before", "Tell places I gave to before when I am allowed to give again")]
    for key, label in fields:
        new = st.toggle(label, value=bool(sw.get(key)), key=f"sw_{key}")
        if new != bool(sw.get(key)):
            store.update_user(user["username"], switches={key: new})
            st.rerun()

    st.divider()
    paused = st.toggle("Pause all requests", value=bool(user.get("paused")), key="pause_me")
    if paused != bool(user.get("paused")):
        store.update_user(user["username"], paused=paused)
        st.rerun()
    st.caption("You are asked at most twice a month, pause or no pause.")

    st.divider()
    _h("Your details")
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
    st.divider()
    if not user.get("lab_code"):
        _link_lab_code(user, "me")
    else:
        st.markdown(f'<div class="bs-note">Lab code <b style="color:{INK}">{user["lab_code"]}</b> · '
                    f'{store.LAB_NAME}</div>', unsafe_allow_html=True)


# -------------------------------------------------------------------------------- router

def render(user: dict) -> None:
    goto = st.session_state.pop("_goto", None)
    if goto in PAGES:
        st.session_state["nav"] = goto  # staged before the nav radio is built, so Streamlit allows the write
    page = ui.sidebar(user, PAGES)
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state.get("_last_page") != page:
        st.session_state["_last_page"] = page
        _close_value()
    if page != "SMS test":
        ui.header(page, SUBTITLE[page])
    if page == "Results":
        _results(user)
    elif page == "Needs":
        _needs(user)
    elif page == "Donations":
        _donations(user)
    elif page == "Ask":
        from views.ai_panel import chat
        chat(user, suggestions=SUGGESTIONS)
    elif page == "Notifications":
        ui.notification_list(user["username"], "Nothing yet. The lab and the places write here.")
    elif page == "SMS test":
        from views import sms
        sms.render(user)
    else:
        _me(user)
