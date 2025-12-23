from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions

from .config import settings
from .tools import Fingerprinter

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, collection: str = "knowledge", persist_directory: str | None = None) -> None:
        self.persist_directory = persist_directory or str(Path("data/chroma").resolve())
        self.client = chromadb.PersistentClient(path=self.persist_directory, settings=chromadb.Settings())
        self.collection = self.client.get_or_create_collection(
            name=collection,
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            ),
        )

    def ingest_files(self, paths: Iterable[Path], chunk_size: int = 800, chunk_overlap: int = 80) -> int:
        added = 0
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            fingerprint = Fingerprinter.sha256(path)
            metadata = {"source": str(path), "fingerprint": fingerprint}
            if self._already_ingested(fingerprint):
                continue
            chunks = Fingerprinter.chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            ids = [f"{fingerprint}:{i}" for i in range(len(chunks))]
            self.collection.add(documents=chunks, ids=ids, metadatas=[metadata] * len(chunks))
            added += len(chunks)
            logger.info("ingested", extra={"file": str(path), "chunks": len(chunks)})
        return added

    def query(self, text: str, k: int = 4) -> list[dict]:
        results = self.collection.query(query_texts=[text], n_results=k)
        docs = []
        for doc, metadata in zip(results.get("documents", [[]])[0], results.get("metadatas", [[]])[0]):
            docs.append({"text": doc, "metadata": metadata})
        return docs

    def _already_ingested(self, fingerprint: str) -> bool:
        existing = self.collection.get(where={"fingerprint": fingerprint}, limit=1)
        return bool(existing.get("ids"))

    def cleanup(self, collection: str | None = None) -> None:
        target = collection or self.collection.name
        try:
            self.client.delete_collection(target)
        except Exception:  # noqa: BLE001
            logger.warning("cleanup failed", exc_info=True)


def iter_paths(root: str | Path, allowed_exts: tuple[str, ...] = (".md", ".txt", ".pdf")) -> list[Path]:
    root_path = Path(root)
    results: list[Path] = []
    for path in root_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in allowed_exts:
            results.append(path)
    return results
