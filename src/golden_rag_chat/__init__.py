"""Golden-Data RAG chatbot backend.

A small, reusable retrieval-augmented chat backend that serves multiple domains
(Apolo career matching, agriculture advisory) over curated *golden data*.

Design principle: Bedrock-first, but not Bedrock-locked. Every external concern
(retrieval, LLM, combined RAG, user state) is a swappable provider behind a
Protocol. The default configuration runs fully offline with mock providers.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
