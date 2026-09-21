"""Lab side, screen 3: publish the day's batch, the lab's own patients, staff notifications, the donor link.

The lab is where every patient starts. This side holds back what may not be delivered by an app
(urgent values wait for the doctor's phone call), publishes the rest, and passes one single fact
to the donor side: the blood type of patients who switched the donor part on.
"""

from datetime import date

import streamlit as st

import store
import ui

PAGES = ["Publish results", "Data", "Patients", "Notify patients", "Donor link", "Notifications"]

SWITCH_LABELS = {"results": "results", "nearby": "nearby", "gave_before": "gave before"}

# One-click starters for the notify form: title, body, audience.
TEMPLATES = [
    ("Lab closed on Friday", "The lab is closed on Friday. Blood draws move to the next working day. "
                             "Results already on their way are not delayed.", "all"),
    ("Please book your follow-up test", "Your doctor asked for a follow-up blood test. Please book a new "
                                        "appointment at the lab. Bring your lab letter.", "all"),
]


# ------------------------------------------------------------------------------------------ helpers

def _day(iso: str) -> str:
    """2026-09-21 -> 'Mon 21 Sep'."""
    return f"{date.fromisoformat(iso):%a %d %b}".replace(" 0", " ")


def _batch_codes() -> set[str]:
    """Lab codes that have a report in today's batch (store has no such helper)."""
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


def _recipients(audience: str, one: str | None = None) -> list[dict]:
    """Who store.send_message would reach. Mirrors its rules so the count can be shown before sending."""
    out = []
    for p in store.patients():
        if audience == "one":
            if p["username"] == one:
                out.append(p)
        elif audience == "all" and p["switches"].get("results"):
            out.append(p)
        elif audience == "donors" and _donor_on(p):
            out.append(p)
    return out


def _notified_accounts() -> list[dict]:
    """Real accounts that publishing notifies: a report in the batch and the results switch on."""
    codes = _batch_codes()
    return [p for p in store.patients() if p.get("lab_code") in codes and p["switches"].get("results")]


def _preview_value() -> dict:
    """The ferritin line of a batch report: the value card the patient will see."""
    for code, reps in store.REPORTS.items():
        for r in reps:
            if r["id"] in store.BATCH_REPORT_IDS:
                v = next((v for v in r["values"] if v["key"] == "ferritin" and v["flag"] != "In range"), None)
                if v:
                    return v
    return {"name": "Ferritin (iron store)", "value": 18, "unit": "ng/mL", "low": 30, "high": 300, "flag": "Low"}


# ------------------------------------------------------------------------------------ publish page

def _publish(user: dict) -> None:
    b = store.batch()
    ui.header("Publish results", f"Batch of {_day(b['id'])} · from the lab system")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Reports", f"{b['reports']}")
    k2.metric("Ready", f"{b['ready']}")
    k3.metric("Code does not match", f"{b['code_mismatch']}")
    k4.metric("Urgent values", f"{b['urgent']}", help="Never delivered by an app first: the doctor phones.")

    # ------------------------------------------------------------------------------- held back
    st.markdown("#### Held back")
    st.caption("These reports do not go out with the batch. Urgent values are never delivered by an app first: "
               "Release opens only after the doctor's phone call is recorded.")
    for h in b["held"]:
        left, right = st.columns([3, 1.5], vertical_alignment="center")
        state = "Released" if h["released"] else "Doctor has phoned" if h["phoned"] else h["note"]
        left.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{h["code"]}</b>'
                      f'<div class="units">{h["detail"]}</div>'
                      f'<div class="sub">{state}</div></div>', unsafe_allow_html=True)
        if h["released"]:
            right.success("Released to the patient", icon="✅")
            continue
        if h["reason"] == "urgent":
            c1, c2 = right.columns(2)
            if c1.button("Doctor has phoned", key=f"phone_{h['code']}", use_container_width=True,
                         disabled=h["phoned"]):
                store.mark_phoned(h["code"], user["username"])
                st.rerun()
            # Kept visible but disabled before the call, so the rule is readable on the screen.
            if c2.button("Release", key=f"rel_{h['code']}", use_container_width=True, disabled=not h["phoned"],
                         type="primary" if h["phoned"] else "secondary",
                         help="Opens after the phone call is recorded."):
                try:
                    store.release_held(h["code"])
                except ValueError as e:      # the store is the rule; the screen only reports it
                    st.error(str(e))
                else:
                    st.rerun()
        else:
            if right.button("Checked by hand, release", key=f"rel_{h['code']}", use_container_width=True):
                try:
                    store.release_held(h["code"])
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.rerun()

    # -------------------------------------------------------------------------------- publish
    st.markdown("#### Publish")
    notified = _notified_accounts()
    if b["published"]:
        st.markdown(f'<div class="bs-alert ok"><h4>✅ Published</h4><p><b>{b["ready"]} reports</b> published to '
                    f'patients. {len(notified)} patient account{"s" if len(notified) != 1 else ""} on this demo '
                    f'{"were" if len(notified) != 1 else "was"} notified: the rest of the batch waits for people who '
                    f'have not opened the app yet. This batch cannot be published a second time.</p></div>',
                    unsafe_allow_html=True)
    else:
        if st.button(f"Publish {b['ready']} to patients", type="primary", key="publish_batch"):
            count = store.publish_batch(user["username"])
            st.session_state["published_count"] = count
            st.rerun()
        st.caption(f"{b['ready']} of {b['reports']} reports go out. The {len(b['held']) - b['released_count']} held "
                   "back stay here. Patients with the results switch on get a notification.")

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
    st.caption("The text explains the value. It gives no diagnosis and no cause. The doctor does that.")


# ----------------------------------------------------------------------------------- patients page

def _patients() -> None:
    ui.header("Patients", f"Patients of {store.LAB_NAME} with an account")
    codes = _batch_codes()
    rows = []
    for p in sorted(store.patients(), key=lambda x: x["name"]):
        newest = _newest_report(p.get("lab_code"))
        rows.append({
            "Name": p["name"],
            "Lab code": p.get("lab_code") or "",
            "Switches on": _switch_text(p["switches"]) + (" (paused)" if p.get("paused") else ""),
            "Newest report": _day(newest) if newest else "none",
            "In today's batch": "yes" if p.get("lab_code") in codes else "no",
        })
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption("The lab knows its own patients by name. A blood centre never gets this list.")

    st.markdown("#### Lab codes without an account")
    free = store.unclaimed_lab_codes()
    if free:
        st.markdown("\n".join(f"- **{c}**: report of {_day(_newest_report(c))}, waiting for a first open"
                              for c in free))
        st.caption("These reports are published like the rest. They become visible when the person signs up "
                   "with the lab code on their letter.")
    else:
        st.caption("Every lab code in the demo has an account.")


# ------------------------------------------------------------------------------ notify patients page

def _notify(user: dict) -> None:
    ui.header("Notify patients", "A message from the lab, in the app of the people who agreed to hear from it")
    st.session_state.setdefault("sent_log", [])
    # A send empties the form on the next run (widget keys cannot be written once the widgets exist),
    # so a second press cannot send the same message again.
    if st.session_state.pop("notify_reset", False):
        st.session_state.update(notify_title="", notify_body="")
    flash = st.session_state.pop("notify_flash", None)

    st.markdown("###### Templates")
    cols = st.columns(len(TEMPLATES) + 1)
    for i, (title, body, audience) in enumerate(TEMPLATES):
        if cols[i].button(title, key=f"tpl_{i}", use_container_width=True):
            st.session_state.update(notify_title=title, notify_body=body, notify_audience="All patients")
            st.rerun()
    if cols[-1].button("Clear", key="tpl_clear", use_container_width=True):
        st.session_state.update(notify_title="", notify_body="")
        st.rerun()

    title = st.text_input("Title", key="notify_title", placeholder="Lab closed on Friday")
    body = st.text_area("Message", key="notify_body", height=110,
                        placeholder="Plain language. No results and no advice in a group message.")
    audience_label = st.selectbox("Who gets it", ["All patients", "Donors only", "One patient"], key="notify_audience")
    audience = {"All patients": "all", "Donors only": "donors", "One patient": "one"}[audience_label]

    people = sorted(store.patients(), key=lambda p: p["name"])
    one = None
    if audience == "one":
        pick = st.selectbox("Which patient", [f"{p['name']} ({p['lab_code']})" for p in people], key="notify_one")
        one = next((p["username"] for p in people if f"{p['name']} ({p['lab_code']})" == pick), None)

    targets = _recipients(audience, one)
    note = {"all": "patients with the results switch on",
            "donors": "patients with the donor part on and not paused",
            "one": "the selected patient"}[audience]
    st.markdown(f'<div class="bs-card"><b>{len(targets)} '
                f'{"people" if len(targets) != 1 else "person"} will get this</b>'
                f'<div class="units">{note}: {", ".join(p["name"] for p in targets) or "nobody"}</div></div>',
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
        for s in st.session_state["sent_log"]:
            st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{s["title"]}</b>'
                        f'<div class="sub">{s["audience"]} · {s["count"]} '
                        f'{"recipients" if s["count"] != 1 else "recipient"}</div></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------------- donor link page

def _donor_link() -> None:
    b = store.batch()
    ui.header("Donor link", "The one fact the lab passes on")
    st.markdown(f'<div class="bs-card"><b>{b["donor_link"]} patients in this batch switched the donor part on.</b>'
                f'<div class="units">Their blood type is filled in from this result. The lab passes nothing else '
                f'to any blood centre. The figure counts every patient in the batch of {b["reports"]} reports; '
                f'the list below shows only the accounts that exist in this demo.</div></div>', unsafe_allow_html=True)

    st.markdown("#### Demo accounts with the donor part on")
    on = [p for p in sorted(store.patients(), key=lambda p: p["name"]) if _donor_on(p)]
    if on:
        for p in on:
            switches = ", ".join(SWITCH_LABELS[k] for k in ("nearby", "gave_before") if p["switches"].get(k))
            st.markdown(f'<div class="bs-card" style="margin-bottom:8px"><b>{p["name"]}</b>'
                        f'<div class="units">Blood type passed on: <b>{p.get("blood_type") or "filled in at publish"}'
                        f'</b></div><div class="sub">Donor part: {switches}. Nothing else about this person leaves '
                        f'the lab.</div></div>', unsafe_allow_html=True)
    else:
        st.caption("No account has the donor part on.")
    st.caption("Names stand here because the lab already knows them. Only the blood type leaves the lab, "
               "and a blood centre reads it as a count.")

    st.markdown("#### What is not passed")
    st.markdown("- Values: no ferritin, no haemoglobin, no glucose, nothing measured.\n"
                "- Ranges: not the lab's minimum, not its maximum, not whether a value is out of range.\n"
                "- Names of tests: not which tests were done, not how many.\n"
                "- Names, addresses and lab codes of patients.\n"
                "- Anything about a patient who did not switch the donor part on.")
    st.caption("A blood centre asks the system how many people of a blood type it could reach. "
               "It gets a number. It learns a name only when someone books a slot.")


# ---------------------------------------------------------------------------------------- router

def render(user: dict) -> None:
    page = ui.sidebar(user, PAGES)
    if page == "Publish results":
        _publish(user)
    elif page == "Data":
        from views import data
        data.render(user)
    elif page == "Patients":
        _patients()
    elif page == "Notify patients":
        _notify(user)
    elif page == "Donor link":
        _donor_link()
    else:
        ui.header("Notifications", "Messages for this lab account")
        ui.notification_list(user["username"], empty="No notifications for the lab account yet.")
