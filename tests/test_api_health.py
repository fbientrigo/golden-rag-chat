"""Tests for the meta endpoints."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "golden-rag-chat"}


def test_capabilities(client):
    resp = client.get("/capabilities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["domains"] == ["apolo", "agriculture"]
    assert {"mock", "local", "bedrock_kb"} <= set(body["retrieval_backends"])
    assert {"mock", "openrouter", "bedrock_converse", "ollama"} <= set(body["llm_backends"])
    assert {"local_pipeline", "bedrock_retrieve_and_generate"} <= set(body["rag_backends"])
