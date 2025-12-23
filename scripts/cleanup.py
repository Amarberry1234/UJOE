from __future__ import annotations

import argparse
import logging

from uj0e.vector import VectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup(collection: str) -> None:
    store = VectorStore(collection=collection)
    store.cleanup(collection)
    logger.info("collection %s removed", collection)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="knowledge")
    args = parser.parse_args()
    cleanup(args.collection)


if __name__ == "__main__":
    main()
