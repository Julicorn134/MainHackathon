"""Lab side: publish the day's batch, the lab's own patients, blood requests to a centre,
staff notifications, the donor link.

The lab is where every patient starts. This side holds back what may not be delivered by an app
(urgent values wait for the phone call), publishes the rest, orders blood components through the
approved hospital process, and passes one single fact to the donor side: the blood type of
patients who switched the donor part on.

Speed note: every page takes the batch and the patient list as arguments. store.batch() and
store.patients() each read and parse the whole state file, so render() calls each at most once and
only for the page that is actually shown. Tables are plain HTML through st.markdown: st.dataframe
pulls in pandas and the Arrow machinery on first use (about 2 seconds on this machine) for a table
of fifteen rows.
"""

from datetime import date, timedelta
from html import escape

import streamlit as st

import store
import ui

PAGES = ["Publish results", "Data", "Patients", "Blood requests", "Notify patients", "Donor link", "Notifications"]

SWITCH_LABELS = {"results": "results", "nearby": "nearby", "gave_before": "gave before"}

# One-click starters for the notify form: title, body, audience.
TEMPLATES = [
    ("Lab closed on Friday", "The lab is closed on Friday. Blood draws move to the next working day. "
                             "Results already on their way are not delayed.", "all"),
    ("Please book your follow-up test", "Your doctor asked for a follow-up blood test. Please book a new "
                                        "appointment at the lab. Bring your lab letter.", "all"),
]

# Colour per order status. The word is always shown, so colour is never the only carrier.
ORDER_STATUS_COLOR = {
    "submitted": "#4b5563",
    "confirmed": "#15803d",
    "partly available": "#b45309",
    "ready for pickup": "#15803d",
    "delivered": "#1d4ed8",
    "declined": "#c8102e",
}

_CSS = """
<style>
.bs-sec {font-size: 15px; font-weight: 600; color: #111827; margin: 22px 0 6px;}
.bs-help {font-size: 12.5px; color: #5f5d58; margin: 0 0 8px;}
.bs-strip {display: flex; border: 1px solid #e5e4df; border-radius: 10px; background: #fff; margin: 4px 0 4px;}
.bs-strip .m {flex: 1; padding: 12px 16px; border-left: 1px solid #e5e4df;}
.bs-strip .m:first-child {border-left: none;}
.bs-strip .k {font-size: 12px; color: #6b7280;}
.bs-strip .v {font-size: 24px; font-weight: 600; color: #111827; line-height: 1.3;}
.bs-strip .n {font-size: 12.5px; color: #5f5d58;}
.bs-mark {font-size: 12.5px; font-weight: 600;}
.bs-mark i {display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px;
             vertical-align: middle; font-style: normal;}
.bs-table {width: 100%; border-collapse: collapse; background: #fff; font-size: 13px; margin: 2px 0 6px;}
.bs-table th {padding: 8px 12px; text-align: left; font-size: 11.5px; font-weight: 600; color: #6b7280;
              text-transform: uppercase; letter-spacing: .04em; border-bottom: 1px solid #e5e4df;
              white-space: nowrap;}
.bs-table td {padding: 8px 12px; text-align: left; border-bottom: 1px solid #f0efec; color: #4b5563;
              vertical-align: top;}
.bs-table td.n {text-align: right;}
.bs-table th.n {text-align: right;}
.bs-table td:first-child {color: #111827; font-weight: 600;}
.bs-head {font-size: 11.5px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .04em;
          padding-bottom: 6px; border-bottom: 1px solid #e5e4df; margin-bottom: 2px;}
.bs-cell {font-size: 13px; color: #4b5563; line-height: 1.5;}
.bs-cell.k {color: #111827; font-weight: 600;}
[class*="st-key-hbrow-"] {border-bottom: 1px solid #f0efec; padding: 4px 0;}
.bs-panel {border: 1px solid #e5e4df; border-radius: 10px; background: #fff; padding: 14px 18px; margin: 2px 0 8px;}
.bs-panel .t {font-size: 12px; color: #6b7280; margin: 10px 0 2px;}
.bs-panel .t:first-child {margin-top: 0;}
.bs-ev {padding: 6px 0; border-top: 1px solid #f0efec; font-size: 13px; color: #4b5563;}
.bs-ev:first-of-type {border-top: none;}
.bs-ev b {color: #111827;}
.bs-ev .who {font-size: 12px; color: #8a8780;}
</style>
"""


# ------------------------------------------------------------------------------------------ helpers

def _day(iso: str) -> str:
    """2026-09-21 -> 'Mon 21 Sep'."""
    return f"{date.fromisoformat(iso):%a %d %b}".replace(" 0", " ")


def _batch_codes() -> set[str]:
    """Lab codes that have a report in today's batch (store has no such helper, and this reads no file)."""
    return {code for code, reps in store.REPORTS.items()
            if any(r["id"] in store.BATCH_REPORT_IDS for r in reps)}


def _newest_report(code: str) -> str | None:
    """Newest report date the lab holds for a code, published or not."""
    reps = store.REPORTS.get(code, [])
    return max((r["date"] for r in reps), default=None)


def _switch_text(switches: dict) -> str:
    on = [label for key, label in SWITCH_LABELS.items() if switches.get(key)]
    return ", ".join(on) if on else "none"


def _donor_on(p: dict) -> bool:
    """The donor part: at least one of the two donor switches, and not paused."""
    return bool((p["switches"].get("nearby") or p["switches"].get("gave_before")) and not p.get("paused"))


def _recipients(people: list[dict], audience: str, one: str | None = None) -> list[dict]:
    """Who store.send_message would reach. Mirrors its rules so the count can be shown before sending."""
    out = []
    for p in people:
        if audience == "one":
            if p["username"] == one:
                out.append(p)
        elif audience == "all" and p["switches"].get("results"):
            out.append(p)
        elif audience == "donors" and _donor_on(p):
            out.append(p)
    return out


def _notified_accounts(people: list[dict], codes: set[str]) -> list[dict]:
    """Real accounts that publishing notifies: a report in the batch and the results switch on."""
    return [p for p in people if p.get("lab_code") in codes and p["switches"].get("results")]


def _preview_value() -> dict:
    """The ferritin line of a batch report: the value card the patient will see."""
    for code, reps in store.REPORTS.items():
        for r in reps:
            if r["id"] in store.BATCH_REPORT_IDS:
                v = next((v for v in r["values"] if v["key"] == "ferritin" and v["flag"] != "In range"), None)
                if v:
                    return v
    return {"name": "Ferritin (iron store)", "value": 18, "unit": "ng/mL", "low": 30, "high": 300, "flag": "Low"}


def _css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _section(title: str, help_text: str | None = None) -> None:
    """Section heading at 15px/600, with one quiet helper line when it earns its place."""
    block = f'<div class="bs-sec">{escape(title)}</div>'
    if help_text:
        block += f'<div class="bs-help">{escape(help_text)}</div>'
    st.markdown(block, unsafe_allow_html=True)


def _mark(color: str, label: str) -> str:
    """A status mark: dot plus plain coloured text. Never a pill."""
    return (f'<span class="bs-mark" style="color:{color}"><i style="background:{color}"></i>'
            f'{escape(label)}</span>')


def _table(headers: list[str], rows: list[list[str]], numeric: set[int] | None = None) -> None:
    """A plain HTML table. Replaces st.dataframe: same content, aligned columns, no heavy import."""
    numeric = numeric or set()
    head = "".join(f'<th class="{"n" if i in numeric else ""}">{escape(str(h))}</th>'
                   for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(f'<td class="{"n" if i in numeric else ""}">{c}</td>'
                                    for i, c in enumerate(r)) + "</tr>" for r in rows)
    st.markdown(f"<table class='bs-table'><thead><tr>{head}</tr></thead>"
                f"<tbody>{body}</tbody></table>", unsafe_allow_html=True)


def _metric_strip(items: list[tuple[str, str, str]]) -> None:
    """One bordered strip, 1px dividers: label, value, one quiet note."""
    cells = "".join(f'<div class="m"><div class="k">{escape(k)}</div><div class="v">{escape(v)}</div>'
                    f'<div class="n">{escape(n)}</div></div>' for k, v, n in items)
    st.markdown(f'<div class="bs-strip">{cells}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------------------------ publish page

def _publish(user: dict, b: dict, people: list[dict], codes: set[str]) -> None:
    ui.header("Publish results", f"Batch of {_day(b['id'])}")
    _css()

    _metric_strip([
        ("Reports", f"{b['reports']}", "finished this batch day"),
        ("Ready", f"{b['ready']}", "checked, matched, not urgent"),
        ("Code does not match", f"{b['code_mismatch']}", "checked by hand"),
        ("Urgent values", f"{b['urgent']}", "phone call first"),
    ])

    # ------------------------------------------------------------------------------- held back
    _section("Held back", "Urgent values are released after the doctor has phoned the patient. "
                          "A code that does not match is released after a check by hand.")
    widths = [1.0, 2.2, 1.5, 1.5, 2.3]
    h1, h2, h3, h4, h5 = st.columns(widths)
    for col, label in zip((h1, h2, h3, h4, h5), ("Code", "Finding", "Reason", "State", "Action")):
        col.markdown(f'<div class="bs-head">{label}</div>', unsafe_allow_html=True)

    for h in b["held"]:
        with st.container(key=f"hbrow-{h['code']}"):
            c1, c2, c3, c4, c5 = st.columns(widths, vertical_alignment="center")
            reason = "Urgent value" if h["reason"] == "urgent" else "Code does not match"
            if h["released"]:
                state = _mark("#15803d", "Released")
            elif h["phoned"]:
                state = _mark("#b45309", "Phone call recorded")
            else:
                state = _mark("#c8102e" if h["reason"] == "urgent" else "#b45309", "Waiting")
            c1.markdown(f'<div class="bs-cell k">{escape(h["code"])}</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="bs-cell">{escape(h["detail"])}</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="bs-cell">{escape(reason)}</div>', unsafe_allow_html=True)
            c4.markdown(state, unsafe_allow_html=True)
            if h["released"]:
                c5.markdown('<div class="bs-cell">goes out with the batch</div>', unsafe_allow_html=True)
                continue
            if h["reason"] == "urgent":
                a1, a2 = c5.columns(2)
                if a1.button("Record phone call", key=f"phone_{h['code']}", disabled=h["phoned"]):
                    store.mark_phoned(h["code"], user["username"])
                    st.rerun()
                # Kept visible but disabled before the call, so the rule is readable on the screen.
                if a2.button("Release", key=f"rel_{h['code']}", disabled=not h["phoned"]):
                    try:
                        store.release_held(h["code"])
                    except ValueError as e:      # the store is the rule; the screen only reports it
                        st.error(str(e))
                    else:
                        st.rerun()
            else:
                if c5.button("Release after check", key=f"rel_{h['code']}"):
                    try:
                        store.release_held(h["code"])
                    except ValueError as e:
                        st.error(str(e))
                    else:
                        st.rerun()

    # -------------------------------------------------------------------------------- publish
    _section("Publish")
    notified = _notified_accounts(people, codes)
    if b["published"]:
        st.markdown(_mark("#15803d", f"Published · {b['ready']} reports · {len(notified)} accounts notified"),
                    unsafe_allow_html=True)
        st.markdown('<div class="bs-help">A batch is published once.</div>', unsafe_allow_html=True)
    else:
        held_open = len(b["held"]) - b["released_count"]
        st.markdown(f'<div class="bs-help">{b["ready"]} of {b["reports"]} reports go out, '
                    f'{held_open} stay held back. A batch is published once.</div>', unsafe_allow_html=True)
        if st.button("Publish results", type="primary", key="publish_batch"):
            count = store.publish_batch(user["username"])
            st.session_state["published_count"] = count
            st.rerun()

    # --------------------------------------------------------------------- what the patient sees
    _section("What the patient sees")
    v = _preview_value()
    st.markdown(
        f'<div class="bs-card" style="max-width:520px"><div class="bt">{v["name"]}</div>'
        f'<div class="units"><b>{v["value"]} {v["unit"]}</b> · the lab\'s range is {v["low"]} to {v["high"]} '
        f'{v["unit"]}</div>{ui.chip("Medium" if v["flag"] != "In range" else "Low", v["flag"])}'
        f'<div class="sub" style="margin-top:10px;color:#4b5563">'
        f'Ferritin shows how much iron your body has stored. Yours is under the lab\'s minimum.</div></div>',
        unsafe_allow_html=True)
    st.markdown('<div class="bs-help">No diagnosis and no cause: the doctor does that.</div>',
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------------- patients page

def _patients(people: list[dict], codes: set[str]) -> None:
    ui.header("Patients", f"Patients of {store.LAB_NAME} with an account")
    _css()
    q = st.text_input("Filter", key="pat_filter", placeholder="Search a name, lab code or blood type",
                      label_visibility="collapsed").strip().lower()

    rows = []
    for p in sorted(people, key=lambda x: x["name"]):
        newest = _newest_report(p.get("lab_code"))
        code = p.get("lab_code") or ""
        blood = p.get("blood_type") or "not known yet"
        switches = _switch_text(p["switches"]) + (" (paused)" if p.get("paused") else "")
        in_batch = "yes" if code in codes else "no"
        hay = " ".join([p["name"], code, blood, switches]).lower()
        if q and q not in hay:
            continue
        rows.append([escape(p["name"]), escape(code), escape(blood), escape(switches),
                     _day(newest) if newest else "none", in_batch])

    if rows:
        _table(["Name", "Lab code", "Blood type", "Consent switches", "Newest report", "In today's batch"], rows)
        st.markdown(f'<div class="bs-help">{len(rows)} of {len(people)} patients. '
                    f'A blood centre never receives this list.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bs-help">No patient matches this filter.</div>', unsafe_allow_html=True)

    _section("Lab codes without an account")
    free = store.unclaimed_lab_codes()
    if free:
        _table(["Lab code", "Newest report", "State"],
               [[escape(c), _day(_newest_report(c)) or "none", "waiting for a first open"] for c in free])
        st.markdown('<div class="bs-help">Published with the rest. Visible once the person signs up with the '
                    'lab code on their letter.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bs-help">Every lab code has an account.</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------------------ blood requests page

def _blood_requests(user: dict) -> None:
    ui.header("Blood requests", "Order blood components from a blood centre")
    _css()

    notes = [n for n in store.notifications(user["username"]) if n["kind"] in ("network", "order")]
    if notes:
        _section("Notices from the network")
        _table(["From", "Notice", "Detail", "Time"],
               [[escape(n["from"]), escape(n["title"]), escape(n["body"]), n["created_at"][11:16]]
                for n in notes[:4]])

    # ------------------------------------------------------------------------ submit a request
    _section("New request", "What this hospital expects to need, so the centre can reserve it in time.")
    c1, c2 = st.columns(2)
    component = c1.selectbox("Component", store.ORDER_COMPONENTS, key="ord_component")
    blood_type = c2.selectbox("Blood type", store.BLOOD_TYPES, key="ord_blood")

    c3, c4 = st.columns(2)
    units = c3.number_input("Units", min_value=1, max_value=60, value=4, step=1, key="ord_units")
    needed_by = c4.date_input("Needed by", value=store.today() + timedelta(days=3), key="ord_needed")

    place_ids = list(store.PLACES)
    c5, c6 = st.columns(2)
    place = c5.selectbox("Blood centre", place_ids, index=place_ids.index("rbc") if "rbc" in place_ids else 0,
                         format_func=lambda k: store.PLACES[k]["name"], key="ord_place")
    procedure_date = c6.date_input("Procedure date", value=store.today() + timedelta(days=3), key="ord_proc_date")

    c7, c8 = st.columns(2)
    procedure = c7.text_input("Planned procedure", key="ord_procedure",
                              placeholder="Hip replacement, theatre 2").strip()
    note = c8.text_input("Note for the blood centre", key="ord_note",
                         placeholder="Anything the centre needs to know").strip()

    approved = st.checkbox("Requested under the approved hospital transfusion process", key="ord_approved")
    if st.button("Submit request", type="primary", key="ord_submit", disabled=not approved):
        text = f"{procedure} on {_day(procedure_date.isoformat())}" if procedure else ""
        store.create_order(user["username"], place, component, blood_type, int(units),
                           needed_by.isoformat(), text, note)
        st.session_state["ord_flash"] = f"{units} units of {blood_type} {component.lower()} requested."
        st.rerun()
    flash = st.session_state.pop("ord_flash", None)
    if flash:
        st.markdown(_mark("#15803d", flash), unsafe_allow_html=True)

    # ------------------------------------------------------------------------- orders and status
    _section("Requests")
    mine = store.orders(by=user["username"])
    if not mine:
        st.markdown('<div class="bs-help">No blood requests yet.</div>', unsafe_allow_html=True)
        return
    _table(["Request", "Component", "Type", "Units", "Needed by", "Blood centre", "Status"],
           [[escape(o["id"]), escape(o["component"]), escape(o["blood_type"]), str(o["units"]),
             _day(o["needed_by"]), escape(store.PLACES[o["to_place"]]["name"]),
             _mark(ORDER_STATUS_COLOR.get(o["status"], "#4b5563"), o["status"].capitalize())]
            for o in mine], numeric={3})

    ids = [o["id"] for o in mine]
    pick = st.selectbox("Order", ids, key="ord_pick")
    o = next((x for x in mine if x["id"] == pick), mine[0])

    lines = []
    if o.get("procedure"):
        lines.append(f'<div class="bs-ev">Procedure · {escape(o["procedure"])}</div>')
    if o.get("note"):
        lines.append(f'<div class="bs-ev">Note · {escape(o["note"])}</div>')
    history = "".join(f'<div class="bs-ev"><b>{escape(h["status"].capitalize())}</b> '
                      f'{escape(h.get("note") or "")}<div class="who">{escape(h["by"])} · '
                      f'{escape(h["at"])}</div></div>' for h in o["history"])
    messages = "".join(f'<div class="bs-ev">{escape(m["text"])}<div class="who">{escape(m["by"])} '
                       f'({escape(m["role"])}) · {escape(m["at"])}</div></div>' for m in o["messages"])
    if not messages:
        messages = '<div class="bs-ev">No messages yet.</div>'
    st.markdown(f'<div class="bs-panel">{"".join(lines)}<div class="t">Status history</div>{history}'
                f'<div class="t">Messages with the blood centre</div>{messages}</div>', unsafe_allow_html=True)

    m1, m2 = st.columns([3, 1], vertical_alignment="bottom")
    reply = m1.text_input("Message to the blood centre", key=f"msg_{o['id']}",
                          placeholder="Ask about availability or delivery.")
    if m2.button("Send message", key=f"send_{o['id']}", disabled=not reply.strip()):
        store.order_message(o["id"], user["username"], reply.strip())
        st.rerun()


# ------------------------------------------------------------------------------ notify patients page

def _notify(user: dict, people: list[dict]) -> None:
    ui.header("Notify patients")
    _css()
    st.session_state.setdefault("sent_log", [])
    # A send empties the form on the next run (widget keys cannot be written once the widgets exist),
    # so a second press cannot send the same message again.
    if st.session_state.pop("notify_reset", False):
        st.session_state.update(notify_title="", notify_body="")
    flash = st.session_state.pop("notify_flash", None)

    c1, c2 = st.columns(2)
    audience_label = c1.selectbox("Who gets it", ["All patients", "Donors only", "One patient"],
                                  key="notify_audience")
    audience = {"All patients": "all", "Donors only": "donors", "One patient": "one"}[audience_label]

    people = sorted(people, key=lambda p: p["name"])
    one = None
    if audience == "one":
        pick = c2.selectbox("Which patient", [f"{p['name']} ({p['lab_code']})" for p in people], key="notify_one")
        one = next((p["username"] for p in people if f"{p['name']} ({p['lab_code']})" == pick), None)

    t1, t2, t3, _pad = st.columns([1.4, 1.8, 0.7, 2.1])
    for col, (i, (title_t, body_t, _aud)) in zip((t1, t2), enumerate(TEMPLATES)):
        if col.button(title_t, key=f"tpl_{i}"):
            st.session_state.update(notify_title=title_t, notify_body=body_t, notify_audience="All patients")
            st.rerun()
    if t3.button("Clear", key="tpl_clear"):
        st.session_state.update(notify_title="", notify_body="")
        st.rerun()

    title = st.text_input("Title", key="notify_title", placeholder="Lab closed on Friday")
    body = st.text_area("Message", key="notify_body", height=110,
                        placeholder="Plain language. No results and no advice in a group message.")

    targets = _recipients(people, audience, one)
    note = {"all": "patients with the results switch on",
            "donors": "patients with the donor part on and not paused",
            "one": "the selected patient"}[audience]
    st.markdown(f'<div class="bs-help">Recipients · {len(targets)} · {escape(note)} · '
                f'{escape(", ".join(p["name"] for p in targets) or "nobody")}</div>', unsafe_allow_html=True)

    if st.button("Send notification", type="primary", key="send_notify", disabled=not (title and body and targets)):
        count = store.send_message(user["username"], audience, title, body, to=one)
        st.session_state["sent_log"].insert(0, {"title": title, "audience": audience_label, "count": count})
        st.session_state.update(notify_reset=True, notify_flash=st.session_state["sent_log"][0])
        st.rerun()

    if flash:  # shown once, right after the send it belongs to
        st.markdown(_mark("#15803d", f'Sent "{flash["title"]}" to {flash["count"]} '
                                     f'{"people" if flash["count"] != 1 else "person"}'),
                    unsafe_allow_html=True)
    if st.session_state["sent_log"]:
        _section("Sent this session")
        _table(["Title", "Audience", "Recipients"],
               [[escape(s["title"]), escape(s["audience"]), str(s["count"])] for s in st.session_state["sent_log"]],
               numeric={2})


# --------------------------------------------------------------------------------- donor link page

def _donor_link(people: list[dict]) -> None:
    ui.header("Donor link", "The one fact the lab passes on")
    _css()
    st.markdown('<div class="bs-help">Passed on: the blood type of patients who opted in. Not passed on: values, '
                'ranges, test names, names, addresses or lab codes. A centre reads blood types as a count and '
                'learns a name only when someone books a slot.</div>', unsafe_allow_html=True)

    on = [p for p in sorted(people, key=lambda p: p["name"]) if _donor_on(p)]
    if on:
        _table(["Name", "Blood type", "Donor switches"],
               [[escape(p["name"]), escape(p.get("blood_type") or "filled in at publish"),
                 escape(", ".join(SWITCH_LABELS[k] for k in ("nearby", "gave_before") if p["switches"].get(k)))]
                for p in on])
    else:
        st.markdown('<div class="bs-help">No account has the donor part on.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------- router

def render(user: dict) -> None:
    """One page is drawn per run, and each store read happens once: the file is parsed per call."""
    page = ui.sidebar(user, PAGES)
    if page == "Publish results":
        _publish(user, store.batch(), store.patients(), _batch_codes())
    elif page == "Data":
        from views import data
        data.render(user)
    elif page == "Patients":
        _patients(store.patients(), _batch_codes())
    elif page == "Blood requests":
        _blood_requests(user)
    elif page == "Notify patients":
        _notify(user, store.patients())
    elif page == "Donor link":
        _donor_link(store.patients())
    else:
        ui.header("Notifications", "Messages for this lab account")
        ui.notification_list(user["username"], empty="No notifications for the lab account yet.")
