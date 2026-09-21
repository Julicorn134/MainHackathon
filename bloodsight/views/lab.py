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

PAGES = ["Publish results", "Patients", "Blood requests", "Notify patients", "Donor link", "Notifications"]

SWITCH_LABELS = {"results": "results", "nearby": "nearby", "gave_before": "gave before"}

# One-click starters for the notify form: title, body, audience.
TEMPLATES = [
    ("Lab closed on Friday", "The lab is closed on Friday. Blood draws move to the next working day. "
                             "Results already on their way are not delayed.", "all"),
    ("Please book your follow-up test", "Your doctor asked for a follow-up blood test. Please book a new "
                                        "appointment at the lab. Bring your lab letter.", "all"),
]

# Colour per order status. The word is always shown, so colour is never the only carrier.
ORDER_STATUS_STYLE = {
    "submitted": ("#52514e", "#f0efec"),
    "confirmed": ("#0a7d0a", "#e6f4e6"),
    "partly available": ("#b97d00", "#fdf3d9"),
    "ready for pickup": ("#0a7d0a", "#e6f4e6"),
    "delivered": ("#2a78d6", "#e8f1fc"),
    "declined": ("#d03b3b", "#fbeaea"),
}

_TABLE_CSS = """
<style>
.bs-table {width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e1e0d9;
           border-radius: 10px; overflow: hidden; font-size: .93rem; margin: 4px 0 6px;}
.bs-table th {padding: 10px 14px; text-align: left; background: #faf9f6; color: #0b0b0b;
              font-weight: 600; white-space: nowrap;}
.bs-table td {padding: 10px 14px; text-align: left; border-top: 1px solid #f0efec; color: #52514e;
              vertical-align: top;}
.bs-table td:first-child {color: #0b0b0b; font-weight: 600;}
.bs-thread {border-left: 3px solid #e1e0d9; padding: 2px 0 2px 12px; margin: 6px 0;}
.bs-thread .who {font-size: .8rem; color: #898781;}
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


def _table(headers: list[str], rows: list[list[str]]) -> None:
    """A plain HTML table. Replaces st.dataframe: same content, aligned columns, no heavy import."""
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    st.markdown(f"{_TABLE_CSS}<table class='bs-table'><thead><tr>{head}</tr></thead>"
                f"<tbody>{body}</tbody></table>", unsafe_allow_html=True)


def _order_chip(status: str) -> str:
    color, bg = ORDER_STATUS_STYLE.get(status, ("#52514e", "#f0efec"))
    return (f'<span class="bs-chip" style="background:{bg};color:{color}">'
            f'{escape(status.capitalize())}</span>')


# ------------------------------------------------------------------------------------ publish page

def _publish(user: dict, b: dict, people: list[dict], codes: set[str]) -> None:
    ui.header("Publish results", f"Batch of {_day(b['id'])} · from the lab system")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Reports", f"{b['reports']}")
    k1.caption("All reports the lab system finished for this batch day.")
    k2.metric("Ready", f"{b['ready']}")
    k2.caption("Reports that may go out now: checked, matched, and not urgent.")
    k3.metric("Code does not match", f"{b['code_mismatch']}")
    k3.caption("The lab code on the sample does not match the record. A person checks these by hand.")
    k4.metric("Urgent values", f"{b['urgent']}")
    k4.caption("A value far outside the range. These are never delivered by an app first.")

    # ------------------------------------------------------------------------------- held back
    st.markdown("#### Held back")
    st.caption("A report is held back when it is not safe to deliver it through the app: either the lab code "
               "does not match the record, or a value is urgent. Held reports stay out of the batch until "
               "someone at the lab clears them.")
    for h in b["held"]:
        left, right = st.columns([3, 1.5], vertical_alignment="center")
        state = "Released" if h["released"] else "Doctor has phoned" if h["phoned"] else h["note"]
        left.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{escape(h["code"])}</b>'
                      f'<div class="units">{escape(h["detail"])}</div>'
                      f'<div class="sub">{escape(state)}</div></div>', unsafe_allow_html=True)
        if h["released"]:
            right.success("Released to the patient")
            right.caption("The report is now part of the batch and goes out with it.")
            continue
        if h["reason"] == "urgent":
            c1, c2 = right.columns(2)
            if c1.button("Doctor has phoned", key=f"phone_{h['code']}", use_container_width=True,
                         disabled=h["phoned"]):
                store.mark_phoned(h["code"], user["username"])
                st.rerun()
            # Kept visible but disabled before the call, so the rule is readable on the screen.
            if c2.button("Release", key=f"rel_{h['code']}", use_container_width=True, disabled=not h["phoned"],
                         type="primary" if h["phoned"] else "secondary"):
                try:
                    store.release_held(h["code"])
                except ValueError as e:      # the store is the rule; the screen only reports it
                    st.error(str(e))
                else:
                    st.rerun()
            right.caption("Doctor has phoned: records that the patient was told by telephone. Release: adds the "
                          "report to the batch, and opens only after that call is recorded.")
        else:
            if right.button("Checked by hand, release", key=f"rel_{h['code']}", use_container_width=True):
                try:
                    store.release_held(h["code"])
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.rerun()
            right.caption("Release after a person compared the sample with the record.")

    # -------------------------------------------------------------------------------- publish
    st.markdown("#### Publish")
    notified = _notified_accounts(people, codes)
    if b["published"]:
        st.markdown(f'<div class="bs-alert ok"><h4>Published</h4><p><b>{b["ready"]} reports</b> published to '
                    f'patients. {len(notified)} patient account{"s" if len(notified) != 1 else ""} on this demo '
                    f'{"were" if len(notified) != 1 else "was"} notified: the rest of the batch waits for people who '
                    f'have not opened the app yet. This batch cannot be published a second time.</p></div>',
                    unsafe_allow_html=True)
    else:
        if st.button(f"Publish {b['ready']} to patients", type="primary", key="publish_batch"):
            count = store.publish_batch(user["username"])
            st.session_state["published_count"] = count
            st.rerun()
        st.caption(f"Publishing makes the ready reports visible in the patient app and sends a notification to "
                   f"every patient with the results switch on. {b['ready']} of {b['reports']} reports go out; the "
                   f"{len(b['held']) - b['released_count']} held back stay here. A batch is published once.")

    # --------------------------------------------------------------------- what the patient sees
    st.markdown("#### What the patient sees")
    v = _preview_value()
    st.markdown(
        f'<div class="bs-card" style="max-width:520px"><div class="bt">{v["name"]}</div>'
        f'<div class="units"><b>{v["value"]} {v["unit"]}</b> · the lab\'s range is {v["low"]} to {v["high"]} '
        f'{v["unit"]}</div>{ui.chip("Medium" if v["flag"] != "In range" else "Low", v["flag"])}'
        f'<div class="sub" style="margin-top:10px;color:#52514e">Written by the AI<br>'
        f'Ferritin shows how much iron your body has stored. Yours is under the lab\'s minimum.</div></div>',
        unsafe_allow_html=True)
    st.caption("A preview of one value card from this batch. The text explains the value. It gives no diagnosis "
               "and no cause. The doctor does that.")


# ----------------------------------------------------------------------------------- patients page

def _patients(people: list[dict], codes: set[str]) -> None:
    ui.header("Patients", f"Patients of {store.LAB_NAME} with an account")
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
        st.caption(f"{len(rows)} of {len(people)} patients shown. The lab knows its own patients by name. "
                   "A blood centre never gets this list.")
    else:
        st.caption("No patient matches this filter.")

    st.markdown("#### Lab codes without an account")
    free = store.unclaimed_lab_codes()
    if free:
        _table(["Lab code", "Newest report", "State"],
               [[escape(c), _day(_newest_report(c)) or "none", "waiting for a first open"] for c in free])
        st.caption("These reports are published like the rest. They become visible when the person signs up "
                   "with the lab code on their letter.")
    else:
        st.caption("Every lab code in the demo has an account.")


# ------------------------------------------------------------------------------ blood requests page

def _blood_requests(user: dict) -> None:
    ui.header("Blood requests", "Order blood components from a blood centre")

    notes = [n for n in store.notifications(user["username"]) if n["kind"] in ("network", "order")]
    if notes:
        st.markdown("#### Notices from the network")
        for n in notes[:4]:
            st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{escape(n["title"])}</b>'
                        f'<div class="units">{escape(n["body"])}</div>'
                        f'<div class="sub">{escape(n["from"])} · {n["created_at"][11:16]}</div></div>',
                        unsafe_allow_html=True)
        st.caption("Supply constraints and answers on your orders arrive here first.")

    # ------------------------------------------------------------------------ submit a request
    st.markdown("#### Submit an expected blood requirement")
    st.caption("States what this hospital expects to need, so the blood centre can reserve it in time.")
    c1, c2, c3 = st.columns(3)
    component = c1.selectbox("Component", store.ORDER_COMPONENTS, key="ord_component")
    blood_type = c2.selectbox("Blood type", store.BLOOD_TYPES, key="ord_blood")
    units = c3.number_input("Units", min_value=1, max_value=60, value=4, step=1, key="ord_units")

    place_ids = list(store.PLACES)
    c4, c5 = st.columns(2)
    place = c4.selectbox("Blood centre", place_ids, index=place_ids.index("rbc") if "rbc" in place_ids else 0,
                         format_func=lambda k: store.PLACES[k]["name"], key="ord_place")
    needed_by = c5.date_input("Needed by", value=store.today() + timedelta(days=3), key="ord_needed")

    c6, c7 = st.columns(2)
    procedure = c6.text_input("Planned procedure", key="ord_procedure",
                              placeholder="Hip replacement, theatre 2").strip()
    procedure_date = c7.date_input("Procedure date", value=store.today() + timedelta(days=3), key="ord_proc_date")
    note = st.text_area("Note for the blood centre", key="ord_note", height=80,
                        placeholder="Anything the centre needs to know about this requirement.").strip()

    approved = st.checkbox("Requested under the approved hospital transfusion process", key="ord_approved")
    if st.button("Submit request", type="primary", key="ord_submit", disabled=not approved):
        text = f"{procedure} on {_day(procedure_date.isoformat())}" if procedure else ""
        store.create_order(user["username"], place, component, blood_type, int(units),
                           needed_by.isoformat(), text, note)
        st.session_state["ord_flash"] = f"{units} units of {blood_type} {component.lower()} requested."
        st.rerun()
    if not approved:
        st.caption("Confirm the approved transfusion process before the request can be submitted.")
    flash = st.session_state.pop("ord_flash", None)
    if flash:
        st.success(flash)

    # ------------------------------------------------------------------------- orders and status
    st.markdown("#### Your requests")
    mine = store.orders(by=user["username"])
    if not mine:
        st.caption("No blood requests yet.")
        return
    _table(["Request", "Component", "Type", "Units", "Needed by", "Blood centre", "Status"],
           [[escape(o["id"]), escape(o["component"]), escape(o["blood_type"]), str(o["units"]),
             _day(o["needed_by"]), escape(store.PLACES[o["to_place"]]["name"]), _order_chip(o["status"])]
            for o in mine])
    st.caption("Availability as answered by the blood centre. Each request keeps its own history and thread.")

    for o in mine:
        with st.expander(f"{o['id']} · {o['units']} x {o['blood_type']} {o['component'].lower()} · {o['status']}"):
            if o.get("procedure"):
                st.caption(f"Planned procedure: {o['procedure']}")
            if o.get("note"):
                st.caption(f"Note: {o['note']}")
            st.markdown("**Status history**")
            for h in o["history"]:
                st.markdown(f'<div class="bs-thread"><b>{escape(h["status"].capitalize())}</b>'
                            f'<div class="units">{escape(h.get("note") or "")}</div>'
                            f'<div class="who">{escape(h["by"])} · {escape(h["at"])}</div></div>',
                            unsafe_allow_html=True)
            st.markdown("**Messages with the blood centre**")
            if o["messages"]:
                for m in o["messages"]:
                    st.markdown(f'<div class="bs-thread"><div class="units">{escape(m["text"])}</div>'
                                f'<div class="who">{escape(m["by"])} ({escape(m["role"])}) · {escape(m["at"])}'
                                f'</div></div>', unsafe_allow_html=True)
            else:
                st.caption("No messages on this request yet.")
            reply = st.text_input("Message to the blood centre", key=f"msg_{o['id']}",
                                  placeholder="Ask about availability or delivery.")
            if st.button("Send message", key=f"send_{o['id']}", disabled=not reply.strip()):
                store.order_message(o["id"], user["username"], reply.strip())
                st.rerun()


# ------------------------------------------------------------------------------ notify patients page

def _notify(user: dict, people: list[dict]) -> None:
    ui.header("Notify patients")
    st.session_state.setdefault("sent_log", [])
    # A send empties the form on the next run (widget keys cannot be written once the widgets exist),
    # so a second press cannot send the same message again.
    if st.session_state.pop("notify_reset", False):
        st.session_state.update(notify_title="", notify_body="")
    flash = st.session_state.pop("notify_flash", None)

    audience_label = st.selectbox("Who gets it", ["All patients", "Donors only", "One patient"], key="notify_audience")
    audience = {"All patients": "all", "Donors only": "donors", "One patient": "one"}[audience_label]

    people = sorted(people, key=lambda p: p["name"])
    one = None
    if audience == "one":
        pick = st.selectbox("Which patient", [f"{p['name']} ({p['lab_code']})" for p in people], key="notify_one")
        one = next((p["username"] for p in people if f"{p['name']} ({p['lab_code']})" == pick), None)

    cols = st.columns(len(TEMPLATES) + 1)
    for i, (title, body, _aud) in enumerate(TEMPLATES):
        if cols[i].button(title, key=f"tpl_{i}", use_container_width=True):
            st.session_state.update(notify_title=title, notify_body=body, notify_audience="All patients")
            st.rerun()
    if cols[-1].button("Clear", key="tpl_clear", use_container_width=True):
        st.session_state.update(notify_title="", notify_body="")
        st.rerun()

    title = st.text_input("Title", key="notify_title", placeholder="Lab closed on Friday")
    body = st.text_area("Message", key="notify_body", height=110,
                        placeholder="Plain language. No results and no advice in a group message.")

    targets = _recipients(people, audience, one)
    note = {"all": "patients with the results switch on",
            "donors": "patients with the donor part on and not paused",
            "one": "the selected patient"}[audience]
    st.markdown(f'<div class="bs-card"><b>{len(targets)} '
                f'{"people" if len(targets) != 1 else "person"} will get this</b>'
                f'<div class="units">{note}: {escape(", ".join(p["name"] for p in targets) or "nobody")}</div></div>',
                unsafe_allow_html=True)

    if st.button("Send notification", type="primary", key="send_notify", disabled=not (title and body and targets)):
        count = store.send_message(user["username"], audience, title, body, to=one)
        st.session_state["sent_log"].insert(0, {"title": title, "audience": audience_label, "count": count})
        st.session_state.update(notify_reset=True, notify_flash=st.session_state["sent_log"][0])
        st.rerun()
    if not (title and body):
        st.caption("A title and a message are needed before sending.")

    if flash:  # shown once, right after the send it belongs to
        st.success(f'Sent "{flash["title"]}" to {flash["count"]} '
                   f'{"people" if flash["count"] != 1 else "person"} ({flash["audience"].lower()}).')
    if st.session_state["sent_log"]:
        st.markdown("#### Sent this session")
        _table(["Title", "Audience", "Recipients"],
               [[escape(s["title"]), escape(s["audience"]), str(s["count"])] for s in st.session_state["sent_log"]])


# --------------------------------------------------------------------------------- donor link page

def _donor_link(people: list[dict]) -> None:
    ui.header("Donor link", "The one fact the lab passes on")
    st.markdown("The lab passes on one fact: the blood type of patients who opted in.")

    on = [p for p in sorted(people, key=lambda p: p["name"]) if _donor_on(p)]
    if on:
        _table(["Name", "Blood type", "Donor switches"],
               [[escape(p["name"]), escape(p.get("blood_type") or "filled in at publish"),
                 escape(", ".join(SWITCH_LABELS[k] for k in ("nearby", "gave_before") if p["switches"].get(k)))]
                for p in on])
    else:
        st.caption("No account has the donor part on.")
    st.caption("Not passed on: values, ranges, test names, names, addresses, lab codes, or anything about a "
               "patient who did not opt in. A blood centre reads the blood type as a count and learns a name "
               "only when someone books a slot.")


# ---------------------------------------------------------------------------------------- router

def render(user: dict) -> None:
    """One page is drawn per run, and each store read happens once: the file is parsed per call."""
    page = ui.sidebar(user, PAGES)
    if page == "Publish results":
        _publish(user, store.batch(), store.patients(), _batch_codes())
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
