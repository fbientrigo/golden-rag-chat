"""Local JSONL golden-data source.

Reads ``<base_dir>/<domain>/golden_chunks.jsonl`` — one JSON object per line, each
validating against :class:`GoldenChunk`. Results are cached per domain.
"""

from __future__ import annotations

import json
from pathlib import Path

from golden_rag_chat.golden_data.contracts import GoldenChunk
from golden_rag_chat.logging import get_logger

logger = get_logger(__name__)


class LocalJsonlGoldenData:
    def __init__(self, base_dir: Path | str, *, filename: str = "golden_chunks.jsonl"):
        self._base_dir = Path(base_dir)
        self._filename = filename
        self._cache: dict[str, list[GoldenChunk]] = {}

    def _path_for(self, domain: str) -> Path:
        return self._base_dir / domain / self._filename

    def load_chunks(self, *, domain: str) -> list[GoldenChunk]:
        if domain in self._cache:
            return self._cache[domain]

        path = self._path_for(domain)
        chunks: list[GoldenChunk] = []
        if not path.exists():
            logger.warning("golden data file missing: %s", path)
            self._cache[domain] = chunks
            return chunks

        with path.open("r", encoding="utf-8") as fh:
            for line_no, raw in enumerate(fh, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    chunks.append(GoldenChunk.model_validate(json.loads(raw)))
                except Exception as exc:  # noqa: BLE001 - log and skip bad lines
                    logger.error("skipping invalid golden chunk at %s:%d: %s", path, line_no, exc)

        self._cache[domain] = chunks
        return chunks
