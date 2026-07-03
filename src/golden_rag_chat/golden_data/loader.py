"""Golden-data source interface.

A ``GoldenDataSource`` returns the curated chunks for a domain. Implementations
read from local files now (JSONL/Parquet) and could read from S3, DynamoDB, or a
Bedrock Knowledge Base export later — without the retrieval layer changing.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from golden_rag_chat.golden_data.contracts import GoldenChunk


@runtime_checkable
class GoldenDataSource(Protocol):
    def load_chunks(self, *, domain: str) -> list[GoldenChunk]: ...
