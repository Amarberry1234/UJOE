from __future__ import annotations

import argparse
import logging
from pathlib import Path

from uj0e.vector import VectorStore, iter_paths

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest(path: str, collection: str, chunk_size: int, chunk_overlap: int) -> None:
    store = VectorStore(collection=collection)
    files = iter_paths(path)
    added = store.ingest_files(files, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    logger.info("added %s chunks", added)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="data/docs")
    parser.add_argument("--collection", default="knowledge")
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    args = parser.parse_args()
    ingest(args.path, args.collection, args.chunk_size, args.chunk_overlap)


if __name__ == "__main__":
    main()
