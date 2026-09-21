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
    """2026-09-22 16:30 -> Tue 22 Sep · 16:30, in store's shared wording. Guarded for a request without slots."""
    return store.slot_label(value) if len(value) >= 16 else value


def _slot_options(days: int, times: list[str] | None = None) -> list[str]:
    """The next `days` days, a few times a day, as "YYYY-MM-DD HH:MM"."""
    start = store.today()
    return [f"{(start + timedelta(days=d)).isoformat()} {t}"
            for d in range(1, days + 1) for t in (times if times is not None else SLOT_TIMES)]


def _message(blood_type: str, slots: list[str]) -> str:
    """The pre-written text people read. Editable afterwards."""
    what = "plasma" if blood_type == store.ANY_TYPE else f"{blood_type} blood"
    head = f"The {PLACE_NAME} expects to run short of {what} next week. You can help prevent it"
    if not slots:
        return f"{head}."
    days = sorted({s[:10] for s in slots})
    span = _day(days[0]) if len(days) == 1 else f"{_day(days[0])} to {_day(days[-1])}"
    return f"{head}: slots from {span}."


def _order(req: dict) -> int:
    """Newest first: REQ-10 is newer than REQ-9, so sort on the number, not the string."""
    return int(req["id"].split("-")[-1])


def _chip(status: str) -> str:
    color, bg, label = _STATUS.get(status, _STATUS["draft"])
    return f'<span class="bs-chip" style="background:{bg};color:{color}">{label}</span>'


def _rules(blood_type: str, radius: int) -> str:
    type_rule = "any blood type (plasma)" if blood_type == store.ANY_TYPE else f"blood type {blood_type}"
    return (f"Matched on: {type_rule}, home within {radius} km, agreed to be asked, "
            f"last gave {store.MIN_DAYS_BETWEEN_DONATIONS} or more days ago, "
            f"asked fewer than {store.MAX_ASKS_PER_MONTH} times this month.")


_PLAIN = 'style="text-align:left;font-weight:400"'          # bs-rec makes the last cell bold and right


# Fixed widths so the columns line up from one request's table to the next down the Bookings page.
_COLS = ('<colgroup><col style="width:22%"><col style="width:18%"><col style="width:11%">'
         '<col style="width:34%"><col style="width:15%"></colgroup>')


def _booking_table(named: list[dict]) -> str:
    head = (f'<tr style="color:#898781;font-size:.8rem"><td>Slot</td><td>Name</td><td>Blood type</td>'
            f'<td>Note</td><td {_PLAIN}>Booked by</td></tr>')
    rows = "".join(
        f"<tr><td>{_slot(b['slot'])}</td><td><b>{b['name']}</b></td><td>{b['blood_type'] or ''}</td>"
        f"<td>{b['note']}</td><td {_PLAIN}>{'app account' if b['real'] else 'simulated'}</td></tr>"
        for b in named)
    return (f'<div class="bs-rec" style="margin-bottom:8px">'
            f'<table style="table-layout:fixed">{_COLS}{head}{rows}</table></div>')


# ------------------------------------------------------------------------------ new request form

FORM_KEYS = ("req_note", "req_seed", "req_days", "req_bt", "req_radius", "req_target", "req_times",
             "req_message", "req_message_auto")


def _init_form() -> None:
    """Seed the form, and fill it from the outlook recommendation when one was handed over.

    Streamlit drops the state of widgets that a run did not draw, so the recommendation is also kept
    in "req_seed": leaving the page and coming back must not quietly change the target under the caption.
    """
    pre = st.session_state.pop("request_prefill", None)
    if pre:
        window = min(max(int(pre.get("window") or 5), 3), 7)
        st.session_state["req_seed"] = {"days": window, "bt": pre["blood_type"], "target": int(pre["target"])}
        st.session_state["req_note"] = (f"Filled in from the recommendation: {int(pre['target'])} donations "
                                        f"in {window} days.")
        for k in ("req_days", "req_bt", "req_target", "req_message", "req_message_auto"):
            st.session_state.pop(k, None)               # the seed below fills these in again
    seed = st.session_state.get("req_seed", {})
    st.session_state.setdefault("req_days", seed.get("days", SIM_DAYS))
    st.session_state.setdefault("req_bt", seed.get("bt", "O-"))
    st.session_state.setdefault("req_radius", 25)
    st.session_state.setdefault("req_target", str(seed.get("target", 200)))
    st.session_state.setdefault("req_times", list(SLOT_TIMES))


def _clear_form() -> None:
    """A created request leaves the form on its own default: the recommendation has been acted on."""
    for k in FORM_KEYS:
        st.session_state.pop(k, None)


MAX_TARGET = 2000


def _target(text: str) -> int | None:
    """The typed target as a whole number, or None when it is not one.

    A number_input silently keeps its old value when staff type something out of range, so the request
    would be sent with a target nobody chose. Here what is sent is what is on screen, or nothing is sent.
    """
    try:
        n = int(str(text).strip())
    except ValueError:
        return None
    return n if 1 <= n <= MAX_TARGET else None


def _open_notice(req: dict) -> str:
    """Why a second request of the same type is refused, in the words of the request that is already open."""
    s = store.request_stats(req["id"])
    return (f"{req['id']} for {req['blood_type']} is open: day {min(req['day'], SIM_DAYS)} of {SIM_DAYS}, "
            f"{s['booked']:,} of {req['target']:,} booked. Close it before sending another.")


def _new_request_form(user: dict) -> None:
    _init_form()
    if st.session_state.get("req_note"):
        st.caption(st.session_state["req_note"])

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        c1, c2 = st.columns(2)
        blood_type = c1.selectbox("Blood type", TYPES, key="req_bt")
        radius = c2.radio("How far from the centre", RADIUS_OPTIONS, key="req_radius", horizontal=True,
                          format_func=lambda km: f"{km} km")
        c3, c4 = st.columns(2)
        days = c3.slider("Slots: days from tomorrow", 3, 7, key="req_days")
        times = c4.multiselect("Times a day", SLOT_TIMES, key="req_times")
        slots = _slot_options(days, times)
        st.caption(f"{len(slots)} slots offered: {_day(store.today() + timedelta(days=1))} to "
                   f"{_day(store.today() + timedelta(days=days))}"
                   + (f", at {', '.join(times)}." if times else ". Choose at least one time."))
        target = _target(st.text_input("Target donations", key="req_target",
                                       help=f"A whole number of donations, from 1 to {MAX_TARGET:,}."))
        if target is None:
            st.caption(f"Target donations must be a whole number from 1 to {MAX_TARGET:,}.")
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

    # One open request per blood type: a second one would ask the same people twice and count them twice.
    already_open = store.open_request(PLACE, blood_type)
    if already_open:
        st.warning(_open_notice(already_open))

    b1, b2, _ = st.columns([1.2, 1, 2.2])
    problem = ("Choose at least one slot." if not slots else
               "Write the message people read." if not message.strip() else
               f"Set a target of at least 1 donation, at most {MAX_TARGET:,}." if target is None else None)
    if b1.button(f"Send to {m['total']:,} people", type="primary", use_container_width=True, key="send_new",
                 disabled=already_open is not None,
                 help=_open_notice(already_open) if already_open else None):
        if problem:
            st.error(problem)
        else:
            try:
                req = store.create_request(user["username"], PLACE, blood_type, radius, slots,
                                           int(target), message.strip(), send=True)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["req_flash"] = f"{req['id']} sent to {req['matched']['total']:,} people."
                _clear_form()
                st.session_state["req_form_open"] = False       # the sent card below is the next thing to read
                st.rerun()
    if b2.button("Save draft", use_container_width=True, key="save_draft"):
        if problem:
            st.error(problem)
        else:
            try:
                req = store.create_request(user["username"], PLACE, blood_type, radius, slots,
                                           int(target), message.strip(), send=False)
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["req_flash"] = f"{req['id']} saved as a draft. You can send it later."
                _clear_form()
                st.session_state["req_form_open"] = False
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
                try:
                    store.send_request(req["id"])
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.session_state["req_flash"] = f"{req['id']} sent."
                    st.rerun()
            return

        st.markdown(f"**Day {min(req['day'], SIM_DAYS)} of {SIM_DAYS}**")
        k = st.columns(4)
        k[0].metric("Asked", f"{stats['asked']:,}")
        k[1].metric("Seen", f"{stats['seen']:,}")
        k[2].metric("Booked", f"{stats['booked']:,}")
        k[3].metric("Not this time", f"{stats['not_this_time']:,}")
        # The bar stops at full; the text keeps the true numbers, so an over-target request reads honestly.
        st.progress(min(stats["booked"] / max(req["target"], 1), 1.0),
                    text=f"{stats['booked']:,} of {req['target']:,} booked"
                         + (" · target reached" if stats["booked"] >= req["target"] else ""))

        bk = store.request_bookings(req["id"], sample=3)
        if bk["named"]:
            st.markdown(_booking_table(bk["named"]), unsafe_allow_html=True)
            if bk["more"]:
                st.caption(f"{bk['more']:,} more on the Bookings page.")
        else:
            st.caption("No bookings yet. A name appears only when someone books a slot.")

        if req["status"] == "closed":
            if req.get("closed_reason") == "target reached":
                st.success(f"Target reached: {stats['booked']:,} booked, target {req['target']:,}. "
                           "The request closed itself.")
            else:
                st.caption(f"Closed: {req.get('closed_reason', 'closed by staff')}.")
            return
        # Closing is not only a status change: it cancels the slots people booked, so say so before the click.
        real_booked = sum(1 for b in bk["named"] if b["real"])
        plural = "s" if real_booked != 1 else ""
        close_help = ("Closing takes the request off everyone's Needs, cancels the slots booked on it "
                      "and tells those people their slot is no longer needed.")
        st.caption(close_help + (f" {real_booked} slot{plural} booked by an app account "
                                 f"{'are' if real_booked != 1 else 'is'} on this request."
                                 if real_booked else ""))
        confirm = True
        if real_booked:
            confirm = st.checkbox(f"Also cancel {real_booked} booked slot{plural}", key=f"confirm_close_{req['id']}")
        a1, a2, _ = st.columns([1.2, 1, 2.2])
        if a1.button("Simulate next day", key=f"day_{req['id']}", help="Demo control: moves this request one day "
                     "forward in the simulated response curve.", disabled=req["day"] >= SIM_DAYS):
            store.advance_day(req["id"])
            st.rerun()
        if a2.button("Close request", key=f"close_{req['id']}", help=close_help, disabled=not confirm):
            store.close_request(req["id"])
            st.session_state["req_flash"] = (
                f"{req['id']} closed. It disappears from everyone's Needs."
                + (f" {real_booked} booked slot{plural} cancelled, those people were told." if real_booked else ""))
            st.rerun()


def _requests_page(user: dict, flash: str | None) -> None:
    ui.header("Requests", "A request, before and after sending.")
    if flash:
        st.success(flash)
    if st.session_state.get("request_prefill"):
        st.session_state["req_form_open"] = True        # the outlook handed a recommendation over: open the form
    with st.expander("New request", expanded=st.session_state.setdefault("req_form_open", True)):
        _new_request_form(user)
    st.divider()
    st.markdown("#### This centre's requests")
    mine = sorted(store.requests(PLACE), key=_order, reverse=True)      # newest first
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
    for req in sorted(live, key=_order, reverse=True):
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
    page = ui.sidebar(user, PAGES)          # the outlook's handover jumps here through ui.sidebar's "_goto"
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
