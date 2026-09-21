"""Blood centre side: Outlook, Requests (a request before and after sending), Bookings, Notifications.

The centre never gets names out of the matching step: it sees a count. A name appears only through
store.request_bookings, which is fed by people who actually booked a slot.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

import store
import ui

PAGES = ["Outlook", "Requests", "Bookings", "Notifications"]
PLACE = "rbc"                                  # this screen belongs to the Regional Blood Centre
PLACE_NAME = store.PLACES[PLACE]["name"]
SIM_DAYS = 5                                   # store's simulated response curve runs five days
SLOT_TIMES = ["09:00", "13:00", "16:30"]       # a few times a day
RADIUS_OPTIONS = [10, 25, 50]
TYPES = store.BLOOD_TYPES + [store.ANY_TYPE]

# Status chips for a request. ui.chip carries the forecast risk colors, which mean something else here.
_STATUS = {"draft": ("#52514e", "#f0efec", "Draft"),
           "sent": ("#2a78d6", "#e8f1fc", "Sent"),
           "closed": ("#0a7d0a", "#e6f4e6", "Closed")}


# ------------------------------------------------------------------------- formatting helpers

def _day(value: str | date) -> str:
    """2026-09-22 -> Tue 22 Sep."""
    d = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    return f"{d:%a %d %b}".replace(" 0", " ")


def _slot(value: str) -> str:
    """2026-09-22 16:30 -> Tue 22 Sep · 16:30."""
    return f"{_day(value)} · {value[11:16]}" if len(value) > 10 else _day(value)


def _slot_options(days: int) -> list[str]:
    """The next `days` days, a few times a day, as "YYYY-MM-DD HH:MM"."""
    start = store.today()
    return [f"{(start + timedelta(days=d)).isoformat()} {t}" for d in range(1, days + 1) for t in SLOT_TIMES]


def _message(blood_type: str, slots: list[str]) -> str:
    """The pre-written text people read. Editable afterwards."""
    what = "plasma" if blood_type == store.ANY_TYPE else f"{blood_type} blood"
    head = f"The {PLACE_NAME} expects to run short of {what} next week. You can help prevent it"
    if not slots:
        return f"{head}."
    days = sorted({s[:10] for s in slots})
    span = _day(days[0]) if len(days) == 1 else f"{_day(days[0])} to {_day(days[-1])}"
    return f"{head}: slots from {span}."


def _chip(status: str) -> str:
    color, bg, label = _STATUS.get(status, _STATUS["draft"])
    return f'<span class="bs-chip" style="background:{bg};color:{color}">{label}</span>'


def _rules(blood_type: str, radius: int) -> str:
    type_rule = "any blood type (plasma)" if blood_type == store.ANY_TYPE else f"blood type {blood_type}"
    return (f"Matched on: {type_rule}, home within {radius} km, agreed to be asked, "
            f"last gave {store.MIN_DAYS_BETWEEN_DONATIONS} or more days ago, "
            f"asked fewer than {store.MAX_ASKS_PER_MONTH} times this month.")


def _booking_table(named: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{_slot(b['slot'])}</td><td><b>{b['name']}</b></td><td>{b['blood_type'] or ''}</td>"
        f"<td>{b['note']}</td><td>{'app account' if b['real'] else 'simulated'}</td></tr>" for b in named)
    return f'<div class="bs-rec" style="margin-bottom:8px"><table>{rows}</table></div>'


# ------------------------------------------------------------------------------ new request form

def _init_form() -> None:
    """Seed the form, and fill it from the outlook recommendation when one was handed over."""
    pre = st.session_state.pop("request_prefill", None)
    if pre:
        window = min(max(int(pre.get("window") or 5), 3), 7)
        st.session_state["req_days"] = window
        st.session_state["req_bt"] = pre["blood_type"]
        st.session_state["req_radius"] = 25
        st.session_state["req_target"] = int(pre["target"])
        st.session_state["req_slots"] = _slot_options(window)
        st.session_state["req_note"] = (f"Filled in from the recommendation: {int(pre['target'])} donations "
                                        f"in {window} days.")
        st.session_state.pop("req_message", None)       # the text is rebuilt for this blood type
        st.session_state.pop("req_message_auto", None)
    st.session_state.setdefault("req_days", SIM_DAYS)
    st.session_state.setdefault("req_bt", "O-")
    st.session_state.setdefault("req_radius", 25)
    st.session_state.setdefault("req_target", 200)
    st.session_state.setdefault("req_slots", _slot_options(st.session_state["req_days"]))


def _new_request_form(user: dict) -> None:
    _init_form()
    st.markdown("#### New request")
    if st.session_state.get("req_note"):
        st.caption(st.session_state["req_note"])

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        c1, c2 = st.columns(2)
        blood_type = c1.selectbox("Blood type", TYPES, key="req_bt")
        radius = c2.radio("How far from the centre", RADIUS_OPTIONS, key="req_radius", horizontal=True,
                          format_func=lambda km: f"{km} km")
        options = _slot_options(st.session_state["req_days"])
        slots = st.multiselect("Slots offered", options, key="req_slots", format_func=_slot)
        target = st.number_input("Target donations", min_value=1, max_value=2000, step=10, key="req_target")
        # The text is regenerated when the blood type or the slots change, unless staff edited it by hand.
        auto = _message(blood_type, slots)
        if st.session_state.get("req_message", st.session_state.get("req_message_auto")) \
                == st.session_state.get("req_message_auto"):
            st.session_state["req_message"] = auto
        st.session_state["req_message_auto"] = auto
        message = st.text_area("The message people read", key="req_message", height=110)

    with right:
        m = store.match_count(blood_type, radius)
        st.markdown("##### Who gets it")
        st.markdown(
            f'<div class="bs-rec"><b style="font-size:1.35rem">{m["total"]:,} people match</b><table>'
            f'<tr><td>Patients of {store.LAB_NAME}</td><td>{m["patients"]:,}</td></tr>'
            f'<tr><td>Gave at this centre before</td><td>{m["gave_before"]:,}</td></tr>'
            f'<tr><td>Expected bookings</td><td>about {m["expected_bookings"]:,}</td></tr></table></div>',
            unsafe_allow_html=True)
        st.caption(_rules(blood_type, radius))
        st.caption(f"Expected bookings: about {store.EXPECTED_BOOKING_RATE:.0%} of the people asked, "
                   "from earlier requests.")
        st.markdown("**You see a count, not names. A name appears only when that person books a slot.**")

    b1, b2, _ = st.columns([1.2, 1, 2.2])
    problem = ("Choose at least one slot." if not slots else
               "Write the message people read." if not message.strip() else None)
    if b1.button(f"Send to {m['total']:,} people", type="primary", use_container_width=True, key="send_new"):
        if problem:
            st.warning(problem)
        else:
            req = store.create_request(user["username"], PLACE, blood_type, radius, slots,
                                       int(target), message.strip(), send=True)
            st.session_state["req_flash"] = f"{req['id']} sent to {req['matched']['total']:,} people."
            st.rerun()
    if b2.button("Save draft", use_container_width=True, key="save_draft"):
        if problem:
            st.warning(problem)
        else:
            req = store.create_request(user["username"], PLACE, blood_type, radius, slots,
                                       int(target), message.strip(), send=False)
            st.session_state["req_flash"] = f"{req['id']} saved as a draft. You can send it later."
            st.rerun()
    st.caption("The model recommends. A staff member presses send.")


# --------------------------------------------------------------------------------- request list

def _request_card(req: dict) -> None:
    stats = store.request_stats(req["id"])
    with st.container(border=True):
        head, chip = st.columns([3, 1], vertical_alignment="center")
        head.markdown(f"**{req['blood_type']} · {req['id']}** · target {req['target']} donations")
        chip.markdown(f"<div style='text-align:right'>{_chip(req['status'])}</div>", unsafe_allow_html=True)
        sent = f"sent {_day(req['sent_at'])} {req['sent_at'][11:16]}" if req.get("sent_at") else "not sent yet"
        st.caption(f"Within {req['radius_km']} km · {len(req['slots'])} slots · {sent}")

        if req["status"] == "draft":
            st.caption(f"{req['matched']['total']:,} people match. Nobody has been asked yet.")
            if st.button(f"Send to {req['matched']['total']:,} people", type="primary", key=f"send_{req['id']}"):
                store.send_request(req["id"])
                st.session_state["req_flash"] = f"{req['id']} sent."
                st.rerun()
            return

        st.markdown(f"**Day {min(req['day'], SIM_DAYS)} of {SIM_DAYS}**")
        k = st.columns(4)
        k[0].metric("Asked", f"{stats['asked']:,}")
        k[1].metric("Seen", f"{stats['seen']:,}")
        k[2].metric("Booked", f"{stats['booked']:,}")
        k[3].metric("Not this time", f"{stats['not_this_time']:,}")
        st.progress(min(stats["booked"] / max(req["target"], 1), 1.0),
                    text=f"{stats['booked']:,} of {req['target']:,} booked")

        bk = store.request_bookings(req["id"], sample=3)
        if bk["named"]:
            st.markdown(_booking_table(bk["named"]), unsafe_allow_html=True)
            if bk["more"]:
                st.caption(f"{bk['more']:,} more on the Bookings page.")
        else:
            st.caption("No bookings yet. A name appears only when someone books a slot.")

        if req["status"] == "closed":
            st.caption(f"Closed: {req.get('closed_reason', 'closed by staff')}.")
            return
        a1, a2, _ = st.columns([1.2, 1, 2.2])
        if a1.button("Simulate next day", key=f"day_{req['id']}", help="Demo control: moves this request one day "
                     "forward in the simulated response curve.", disabled=req["day"] >= SIM_DAYS):
            store.advance_day(req["id"])
            st.rerun()
        if a2.button("Close request", key=f"close_{req['id']}"):
            store.close_request(req["id"])
            st.session_state["req_flash"] = f"{req['id']} closed. It disappears from everyone's Needs."
            st.rerun()


def _requests_page(user: dict, flash: str | None) -> None:
    ui.header("Requests", "A request, before and after sending.")
    if flash:
        st.success(flash)
    _new_request_form(user)
    st.divider()
    st.markdown("#### This centre's requests")
    mine = sorted(store.requests(PLACE), key=lambda r: r["id"], reverse=True)
    if not mine:
        st.caption("No requests yet. The form above makes the first one.")
        return
    st.caption("Population responses are simulated. Bookings by real accounts of the app are live.")
    for req in mine:
        _request_card(req)


# -------------------------------------------------------------------------------- bookings page

def _bookings_page() -> None:
    ui.header("Bookings", "People who booked a slot. This is the only place a name reaches the centre.")
    live = [r for r in store.requests(PLACE) if r["status"] != "draft"]
    if not live:
        st.caption("No request has been sent yet.")
        return
    st.caption("Bookings by real accounts of the app come first. The rest are simulated for the demo.")
    for req in sorted(live, key=lambda r: r["id"], reverse=True):
        bk = store.request_bookings(req["id"])
        st.markdown(f"##### {req['blood_type']} · {req['id']} · {bk['total']:,} booked")
        if not bk["named"]:
            st.caption("Nobody has booked yet. Everyone else stays a count.")
            continue
        st.markdown(_booking_table(bk["named"]), unsafe_allow_html=True)
        if bk["more"]:
            st.caption(f"{bk['more']:,} more.")


# ------------------------------------------------------------------------------------- render

def render(user: dict) -> None:
    page = ui.sidebar(user, PAGES)
    flash = st.session_state.pop("req_flash", None)
    if page == "Outlook":
        from views import outlook
        ui.header("BloodSight AI", "Blood supply intelligence: see the shortage before it happens.")
        outlook.render(user)
    elif page == "Requests":
        _requests_page(user, flash)
    elif page == "Bookings":
        _bookings_page()
    else:
        ui.header("Notifications", "The centre hears about a booking the moment it is made.")
        ui.notification_list(user["username"], "Nothing yet. Bookings and answers arrive here.")
