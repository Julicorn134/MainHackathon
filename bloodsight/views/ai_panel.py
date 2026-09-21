"""On-demand AI requests only; rerenders never repeat a paid request."""
import streamlit as st

import ai_config
import ai_service
import ui


def show_answer(result, *, key):
    st.markdown(result["answer"])
    for limitation in result["limitations"]:
        st.caption(limitation)
    st.caption(f"Generated via {result.get('provider', 'OpenAI')} · {result['model']} · {result['created_at'][:19]} UTC")
    if st.checkbox("Show source records", key=key + "_sources"):
        st.caption(result["scope"])
        for record in result["evidence"]:
            st.caption(f"{record['id']} · {record['label']}")
            st.json(record["data"])
        if not result["evidence"]:
            st.caption("No supporting records were cited.")


def configured():
    try:
        config = ai_config.settings()
    except ValueError as exc:
        st.error(str(exc))
        return False
    if not config["api_key"]:
        st.info(f"AI is not connected. The app administrator needs to add an {config['provider_label']} API key. "
                "Your data can still be saved and forecasts still run.")
        return False
    destination = "OpenRouter and the selected model provider" if config["provider"] == "openrouter" else "OpenAI"
    st.caption(f"Your question and relevant records are sent to {destination}. Model: {config['model']}.")
    return True


def chat(user, *, source="uploaded", suggestions=None):
    if not configured():
        return
    config = ai_config.settings()
    key = f"ai_history_{user['username']}_{source}_{config['provider']}_{config['model']}"
    log = st.session_state.setdefault(key, [])
    for index, item in enumerate(log):
        with st.chat_message("user"):
            st.markdown(item["question"])
        with st.chat_message("assistant"):
            show_answer(item["result"], key=f"{key}_{index}_{item['result']['created_at']}")
    question = None
    if suggestions is not None:
        # Keep the normal branch's prepared-question layout; only the answer backend changes.
        ui.section("Questions")
        for start in range(0, len(suggestions), 3):
            row = suggestions[start:start + 3]
            for col, text in zip(st.columns(3, gap="small"), row):
                if col.button(text, key=f"sug_{start}_{text}"):
                    question = text
        st.caption("The assistant gives no diagnosis, no cause and no promise that you can give blood.")
    else:
        with st.form(key + "_form", clear_on_submit=True, border=False):
            typed = st.text_input("Ask about these records", max_chars=2000,
                                  placeholder="Which blood type needs attention?")
            if st.form_submit_button("Ask AI", type="primary"):
                question = typed
    if log and st.button("Clear conversation", key=key + "_clear"):
        st.session_state[key] = []
        st.rerun()
    if question is not None:
        try:
            with st.spinner("Reading your records..."):
                result = ai_service.answer(user["username"], question, source=source)
            log.append({"question": question, "result": result})
            del log[:-10]
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def explain_value(user, report, value):
    if not configured():
        return
    # A key includes the report content so a changed record cannot reuse an old explanation.
    config = ai_config.settings()
    key = f"ai_value_{user['username']}_{report['id']}_{value['key']}_{value['value']}_{config['provider']}_{config['model']}"
    if st.button("Explain this recorded value", key=key + "_button"):
        try:
            with st.spinner("Reading your report..."):
                st.session_state[key] = ai_service.answer(
                    user["username"], f"Summarise my recorded {value['name']} value and its supplied laboratory range. "
                    "Explain what the report states and what cannot be determined, without diagnosis or advice.",
                    report_id=report["id"])
        except ValueError as exc:
            st.error(str(exc))
    if key in st.session_state:
        show_answer(st.session_state[key], key=key)
