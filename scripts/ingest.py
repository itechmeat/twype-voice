# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database import session_scope
from src.knowledge_ingestion import EmbeddingClient, EmbeddingSettings, ingest_directory
from src.knowledge_ingestion.manifest import ManifestError

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest local knowledge files into PostgreSQL.")
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing manifest.yaml and source files",
    )
    return parser


def _require_google_api_key() -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")
    return api_key


async def _run(directory: Path) -> int:
    try:
        embedding_client = EmbeddingClient(
            EmbeddingSettings(
                api_key=_require_google_api_key(),
            )
        )

        async with session_scope() as session:
            processed_sources = await ingest_directory(
                directory,
                session=session,
                embedding_client=embedding_client,
            )
    except (ManifestError, RuntimeError) as exc:
        logger.error(str(exc))
        return 1
    except Exception:
        logger.exception("Knowledge ingestion failed")
        return 1

    logger.info("Knowledge ingestion complete: %s sources processed", processed_sources)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(_run(args.directory.resolve()))


if __name__ == "__main__":
    raise SystemExit(main())
