"""On-demand AI requests only; rerenders never repeat a paid request."""
import streamlit as st

import ai_config
import ai_service


def show_answer(result):
    st.markdown(result["answer"])
    for limitation in result["limitations"]:
        st.caption(limitation)
    st.caption(f"Generated via {result.get('provider', 'OpenAI')} · {result['model']} · {result['created_at'][:19]} UTC")
    with st.expander("Records used for this answer"):
        st.caption(result["scope"])
        for record in result["evidence"]:
            st.markdown(f"**{record['id']} — {record['label']}**")
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
    st.caption(f"AI model: {config['model']}. A request sends your question and the relevant test records to {destination}. "
               "Answers are generated on demand and include the records used.")
    return True


def chat(user, *, source="uploaded"):
    if not configured():
        return
    config = ai_config.settings()
    key = f"ai_history_{user['username']}_{source}_{config['provider']}_{config['model']}"
    log = st.session_state.setdefault(key, [])
    if log and st.button("Clear this conversation", key=key + "_clear"):
        st.session_state[key] = []
        st.rerun()
    for item in log:
        with st.chat_message("user"):
            st.markdown(item["question"])
        with st.chat_message("assistant"):
            show_answer(item["result"])
    st.caption("Each question is answered independently using the records currently saved in the app.")
    with st.form(key + "_form", clear_on_submit=True):
        question = st.text_input("Ask about these records", max_chars=2000,
                                 placeholder="Which blood type needs attention?" if user["role"] == "centre" else "How have my recorded values changed?")
        submitted = st.form_submit_button("Ask AI", type="primary")
    if submitted:
        try:
            with st.spinner("Reading the saved records and generating an answer…"):
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
            with st.spinner("Generating an explanation from your report…"):
                st.session_state[key] = ai_service.answer(
                    user["username"], f"Summarise my recorded {value['name']} value and its supplied laboratory range. "
                    "Explain what the report states and what cannot be determined, without diagnosis or advice.",
                    report_id=report["id"])
        except ValueError as exc:
            st.error(str(exc))
    if key in st.session_state:
        show_answer(st.session_state[key])
