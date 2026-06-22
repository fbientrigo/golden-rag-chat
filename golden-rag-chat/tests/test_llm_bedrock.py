"""Tests for the Bedrock backends (all offline — fake boto3 client injected).

A MagicMock client's sync methods (`converse`, `retrieve`, `retrieve_and_generate`)
work transparently under ``asyncio.to_thread``, so boto3 is never imported.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from golden_rag_chat.api.schemas import ChatOptions, ChatRequest
from golden_rag_chat.errors import ProviderNotConfiguredError
from golden_rag_chat.golden_data.contracts import Domain
from golden_rag_chat.llm.base import ChatMessage, GenerationOptions
from golden_rag_chat.llm.bedrock_converse import BedrockConverseLLM, to_converse_messages
from golden_rag_chat.rag.bedrock_retrieve_and_generate import BedrockRetrieveAndGenerate
from golden_rag_chat.retrieval.bedrock_kb import BedrockKnowledgeBaseRetrieval


def _messages() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="QUESTION: What skills am I missing?"),
    ]


# --- 1. pure helper ---


def test_converse_messages_split_system():
    converse_messages, system_blocks = to_converse_messages(_messages())
    assert system_blocks == [{"text": "You are a helpful assistant."}]
    assert converse_messages == [
        {"role": "user", "content": [{"text": "QUESTION: What skills am I missing?"}]}
    ]


# --- 2. Converse generate ---


async def test_bedrock_converse_generate_with_fake_client():
    client = MagicMock()
    client.converse.return_value = {
        "output": {"message": {"content": [{"text": "grounded"}]}},
        "usage": {"inputTokens": 10, "outputTokens": 3},
    }
    provider = BedrockConverseLLM(model_id="some.model", region="us-east-1", client=client)
    result = await provider.generate(
        messages=_messages(), sources=[], options=GenerationOptions()
    )
    assert result.text == "grounded"
    assert result.usage["outputTokens"] == 3


# --- 3. KB retrieval mapping ---


async def test_bedrock_kb_retrieve_maps_results():
    client = MagicMock()
    client.retrieve.return_value = {
        "retrievalResults": [
            {
                "content": {"text": "evidence"},
                "score": 0.9,
                "location": {"type": "S3", "s3Location": {"uri": "s3://kb/doc1.txt"}},
                "metadata": {"title": "Doc 1"},
            }
        ]
    }
    provider = BedrockKnowledgeBaseRetrieval(
        knowledge_base_id="kb-123", region="us-east-1", client=client
    )
    sources = await provider.retrieve(
        domain="apolo", question="q", user_state=None, context={}, max_sources=5
    )
    assert len(sources) == 1
    assert sources[0].text == "evidence"
    assert sources[0].uri == "s3://kb/doc1.txt"
    assert sources[0].metadata["domain"] == "apolo"


# --- 4. managed RetrieveAndGenerate mapping ---


async def test_bedrock_rag_answer_maps_citations():
    client = MagicMock()
    client.retrieve_and_generate.return_value = {
        "output": {"text": "answer"},
        "citations": [
            {
                "retrievedReferences": [
                    {
                        "content": {"text": "ref"},
                        "location": {"type": "S3", "s3Location": {"uri": "s3://kb/doc1.txt"}},
                        "metadata": {"title": "Doc 1"},
                    }
                ]
            }
        ],
    }
    provider = BedrockRetrieveAndGenerate(
        knowledge_base_id="kb-123", model_id="some.model", region="us-east-1", client=client
    )
    request = ChatRequest(
        domain=Domain.APOLO,
        user_id="u",
        question="q",
        options=ChatOptions(max_sources=5),
    )
    response = await provider.answer(request=request, user_state=None)
    assert response.answer == "answer"
    assert len(response.sources) == 1
    assert response.sources[0].excerpt == "ref"
    assert response.diagnostics.rag_backend == "bedrock_retrieve_and_generate"
    assert response.diagnostics.num_sources == 1


# --- 5. config guard (no boto3 import) ---


async def test_bedrock_converse_missing_model_id():
    provider = BedrockConverseLLM(model_id=None, region=None)  # no client, no model
    with pytest.raises(ProviderNotConfiguredError, match="GRC_BEDROCK_MODEL_ID"):
        await provider.generate(
            messages=_messages(), sources=[], options=GenerationOptions()
        )


# --- 6. registry accepts bedrock; unconfigured -> 501 ---


def test_chat_bedrock_unconfigured_returns_501(client):
    resp = client.post(
        "/chat",
        json={
            "domain": "apolo",
            "user_id": "u",
            "question": "test",
            "options": {
                "retrieval_backend": "mock",
                "llm_backend": "bedrock_converse",
                "rag_backend": "local_pipeline",
            },
        },
    )
    # No GRC_BEDROCK_MODEL_ID in test env → ProviderNotConfiguredError → 501,
    # proving the registry now accepts bedrock_converse (failure is config, not capability).
    assert resp.status_code == 501
    assert resp.json()["error"] == "provider_not_configured"
