"""Local Parquet golden-data source (optional).

Skeleton. Mirrors :class:`LocalJsonlGoldenData` but reads Parquet. Requires the
``parquet`` extra (``uv pip install -e '.[parquet]'``). Not used by the default
offline test suite, so ``pyarrow`` is never a hard dependency.

Expected layout: ``<base_dir>/<domain>/golden_chunks.parquet`` with one row per
chunk and columns matching :class:`GoldenChunk` fields (``metadata`` may be a JSON
string or a nested struct).
"""

from __future__ import annotations

from pathlib import Path

from golden_rag_chat.golden_data.contracts import GoldenChunk


class LocalParquetGoldenData:
    def __init__(self, base_dir: Path | str, *, filename: str = "golden_chunks.parquet"):
        self._base_dir = Path(base_dir)
        self._filename = filename
        self._cache: dict[str, list[GoldenChunk]] = {}

    def load_chunks(self, *, domain: str) -> list[GoldenChunk]:  # pragma: no cover - skeleton
        raise NotImplementedError(
            "Parquet golden-data loading is not implemented yet. Install the "
            "'parquet' extra and implement with pyarrow when needed."
        )
