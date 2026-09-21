import json

import httpx
from openai import OpenAI
import pytest

import ai_service as ai
import data_store
import store


def mock_provider(monkeypatch, *, source_ids=None, status=200):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-placeholder")
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "SENSITIVE PROVIDER BODY",
                                                          "type": "test_error"}})
        answer = {"answer": "The recorded value is 33 ng/mL.", "source_ids": source_ids or ["E2"],
                  "limitations": ["Synthetic test records."], "cannot_answer": False}
        return httpx.Response(200, json={"id": "resp_test", "object": "response", "created_at": 1,
            "status": "completed", "model": "gpt-4.1-mini", "output": [{"type": "message", "id": "msg_test",
                "role": "assistant", "status": "completed", "content": [{"type": "output_text",
                    "text": json.dumps(answer), "annotations": []}]}]})

    monkeypatch.setattr(ai, "OpenAI", lambda **kw: OpenAI(**kw, http_client=httpx.Client(transport=httpx.MockTransport(handler))))
    return calls


def test_missing_key_never_uses_template():
    with pytest.raises(ai.AIUnavailable, match="not connected"):
        ai.answer("patient", "What are my values?")


def test_actual_sdk_request_and_citations(monkeypatch, report):
    data_store.import_reports("lab", json.dumps([report]).encode())
    rid = data_store.lab_reports("lab")[0]["id"]
    data_store.publish_report("lab", rid)
    calls = mock_provider(monkeypatch)
    result = ai.answer("patient", "Summarise my latest report")
    assert result["evidence"][0]["label"].startswith("Report IMP-")
    request = calls[0]
    assert request["store"] is False
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["max_output_tokens"] == 1800
    assert "tools" not in request
    packet = json.loads(request["input"])
    serial = json.dumps(packet)
    assert "33" in serial
    for secret in ("password_hash", "Alex Jansen", "BL-4790", "postcode", "salt"):
        assert secret not in serial


def test_unknown_source_rejected(monkeypatch):
    mock_provider(monkeypatch, source_ids=["invented-report"])
    with pytest.raises(ai.AIUnavailable, match="linked"):
        ai.answer("patient", "Summarise")


@pytest.mark.parametrize("status", [401, 429, 500])
def test_provider_errors_do_not_expose_bodies(monkeypatch, status):
    mock_provider(monkeypatch, status=status)
    with pytest.raises(ai.AIUnavailable) as exc:
        ai.answer("patient", "Summarise")
    assert "SENSITIVE" not in str(exc.value)


def test_lab_or_unknown_account_cannot_access_patient_context(monkeypatch):
    calls = mock_provider(monkeypatch)
    for user in ("lab", "does-not-exist"):
        with pytest.raises(ValueError):
            ai.answer(user, "Show patient records")
    assert calls == []


def test_paused_and_results_disabled_are_respected():
    store.update_user("patient", paused=True, switches={"results": False})
    packet = ai.evidence_for("patient")
    assert not any(e["label"].startswith("Report") for e in packet["evidence"])
    assert next(e for e in packet["evidence"] if e["label"].startswith("Open needs"))["data"] == []
