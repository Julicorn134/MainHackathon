import json
from pathlib import Path

import httpx
from openai import OpenAI
import pytest
from streamlit.testing.v1 import AppTest

import ai_config
import ai_service as ai


def mock_router(monkeypatch, *, status=200, finish="stop", content=None, refusal=None):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-unit-test-only")
    # A configured alternative provider must never receive this request.
    monkeypatch.setenv("OPENAI_API_KEY", "other-provider-test-only")
    calls = []
    answer = {"answer": "Your report records ferritin at 33 ng/mL.", "source_ids": ["E2"],
              "limitations": ["Synthetic records."], "cannot_answer": False}

    def handler(request):
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-or-unit-test-only"
        calls.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "PRIVATE RESPONSE BODY", "code": status}})
        return httpx.Response(200, json={"id":"gen-test", "object":"chat.completion", "created":1,
            "model":"openai/gpt-4.1-mini", "choices":[{"index":0,"finish_reason":finish,
                "message":{"role":"assistant", "content":content if content is not None else json.dumps(answer),
                           "refusal":refusal}}]})

    monkeypatch.setattr(ai, "OpenAI", lambda **kw: OpenAI(**kw, http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    return calls


def test_openrouter_request_uses_schema_correct_host_and_evidence(monkeypatch):
    calls = mock_router(monkeypatch)
    result = ai.answer("patient", "Summarise my latest report")
    assert result["provider"] == "OpenRouter"
    assert result["model"] == "openai/gpt-4.1-mini"
    assert result["evidence"][0]["id"] == "E2"
    body = calls[0]
    assert body["max_tokens"] == 1800 and body["store"] is False
    assert body["provider"] == {"require_parameters":True,"data_collection":"deny","allow_fallbacks":False}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert "tools" not in body
    packet = json.loads(body["messages"][1]["content"])
    assert packet["question"] == "Summarise my latest report"
    for secret in ("password_hash", "Alex Jansen", "BL-4790", "postcode", "salt", "sk-or-"):
        assert secret not in json.dumps(packet)


@pytest.mark.parametrize("status,message", [(401,"rejected"),(402,"insufficient credits"),
                                          (429,"quota"),(500,"failed")])
def test_router_errors_are_actionable_and_never_retried(monkeypatch,status,message):
    calls = mock_router(monkeypatch,status=status)
    with pytest.raises(ai.AIUnavailable,match=message) as caught:
        ai.answer("patient","Summarise")
    assert "PRIVATE" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize("kwargs", [
    {"finish":"length"}, {"refusal":"Cannot answer"}, {"content":""}, {"content":"PRIVATE invalid JSON"},
    {"content":json.dumps({"answer":"PRIVATE incomplete schema"})},
    {"content":json.dumps({"answer":"PRIVATE unknown source","source_ids":["E999"],"limitations":[],"cannot_answer":False})},
])
def test_invalid_or_incomplete_router_answers_are_not_shown(monkeypatch,kwargs):
    mock_router(monkeypatch,**kwargs)
    with pytest.raises(ai.AIUnavailable) as caught:
        ai.answer("patient","Summarise")
    assert "PRIVATE" not in str(caught.value)


def test_provider_keys_do_not_fall_back_to_each_other(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER","openrouter")
    monkeypatch.setenv("OPENAI_API_KEY","openai-test-only")
    assert ai_config.settings()["api_key"] == ""
    with pytest.raises(ai.AIUnavailable,match="OPENROUTER_API_KEY"):
        ai.answer("patient","Summarise")
    monkeypatch.setenv("AI_PROVIDER","openai")
    monkeypatch.setenv("OPENAI_API_KEY","sk-or-test-only")
    with pytest.raises(ValueError,match="OpenRouter key"):
        ai_config.settings()


def test_auto_provider_and_explicit_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY","sk-or-test-only")
    monkeypatch.setenv("OPENROUTER_MODEL","test/selected-model")
    config = ai_config.settings()
    assert config["provider"] == "openrouter" and config["model"] == "test/selected-model"
    assert config["base_url"] == "https://openrouter.ai/api/v1"
    monkeypatch.setenv("AI_PROVIDER","invalid")
    with pytest.raises(ValueError,match="AI_PROVIDER"):
        ai_config.settings()


def test_router_answer_appears_in_app_without_repeat_request(monkeypatch):
    calls = mock_router(monkeypatch)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"),default_timeout=30)
    app.session_state["username"] = "patient"
    app.session_state["nav"] = "Ask"
    app.run()
    assert not app.exception and len(calls) == 0
    assert not app.text_input  # The donor keeps the bloodsight branch's prepared-question design.
    next(b for b in app.button if b.label == "What does my ferritin mean?").click().run()
    assert not app.exception and len(calls) == 1
    assert any("Generated via OpenRouter" in c.value for c in app.caption)
    app.run()
    assert len(calls) == 1
