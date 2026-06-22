"""End-to-end /chat tests against mock and local backends (fully offline)."""

from __future__ import annotations


def _chat(client, **override):
    body = {
        "domain": "apolo",
        "user_id": "demo-user",
        "session_id": "demo-session",
        "question": "What skills am I missing for data engineering roles?",
        "context": {
            "career_id": "uchile-ingcivil",
            "target_role_family": "Data & Analytics Engineering",
        },
        "options": {
            "retrieval_backend": "mock",
            "llm_backend": "mock",
            "rag_backend": "local_pipeline",
            "max_sources": 5,
        },
    }
    body.update(override)
    return client.post("/chat", json=body)


def test_chat_apolo_mock(client):
    resp = _chat(client)
    assert resp.status_code == 200
    data = resp.json()

    assert data["answer"]
    assert len(data["sources"]) == 1
    source = data["sources"][0]
    assert source["metadata"]["domain"] == "apolo"
    assert source["excerpt"]
    # Grounding: the answer must reference the retrieved source by title.
    assert source["title"] in data["answer"]

    diag = data["diagnostics"]
    assert diag == {
        "domain": "apolo",
        "retrieval_backend": "mock",
        "llm_backend": "mock",
        "rag_backend": "local_pipeline",
        "num_sources": 1,
    }


def test_chat_agriculture_mock(client):
    resp = _chat(
        client,
        domain="agriculture",
        user_id="demo-farm-user",
        question="Why are my grapes at risk after a humid week?",
        context={"selected_crop": "grape"},
        options={"retrieval_backend": "mock", "llm_backend": "mock", "rag_backend": "local_pipeline"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"][0]["metadata"]["domain"] == "agriculture"
    assert data["diagnostics"]["domain"] == "agriculture"


def test_chat_unsupported_retrieval_backend_returns_400(client):
    resp = _chat(
        client,
        options={"retrieval_backend": "does-not-exist", "llm_backend": "mock", "rag_backend": "local_pipeline"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "unsupported_backend"


def test_chat_not_enabled_llm_backend_returns_501(client):
    resp = _chat(
        client,
        options={"retrieval_backend": "mock", "llm_backend": "openrouter", "rag_backend": "local_pipeline"},
    )
    assert resp.status_code == 501
    assert resp.json()["error"] == "provider_not_configured"


def test_chat_local_insufficient_evidence(client):
    # Gibberish question + empty context -> local retrieval finds nothing ->
    # the pipeline must return the domain insufficiency message and no sources,
    # without fabricating an answer.
    resp = _chat(
        client,
        question="zzzqqq nonexistent gibberish token",
        context={},
        options={"retrieval_backend": "local", "llm_backend": "mock", "rag_backend": "local_pipeline"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sources"] == []
    assert data["diagnostics"]["num_sources"] == 0
    assert "enough" in data["answer"].lower()


def test_chat_local_retrieves_real_chunks(client):
    resp = _chat(
        client,
        options={"retrieval_backend": "local", "llm_backend": "mock", "rag_backend": "local_pipeline"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnostics"]["retrieval_backend"] == "local"
    assert any(s["source_id"] == "apolo-skill-gap-001" for s in data["sources"])
