"""Build a Gemini embedding and FAISS index from Phase 2 section records.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --batch-size 25 --delay 1
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai


def load_records(source: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(source.glob("*.json")):
        if path.name in {"split_report.json", "qc_report.json"}:
            continue
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        raise RuntimeError(f"no section records found in {source}")
    return records


def embedding_text(record: dict) -> str:
    return (
        f"{record['act_name']}\n"
        f"{record['section_number']} {record.get('heading', '')}\n"
        f"{record['text']}"
    )


def embed_batch(client: genai.Client, model: str, texts: list[str], retries: int) -> list[list[float]]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = client.models.embed_content(model=model, contents=texts)
            vectors = [list(embedding.values) for embedding in response.embeddings]
            if len(vectors) != len(texts):
                raise RuntimeError(
                    f"embedding response contained {len(vectors)} vectors for {len(texts)} texts"
                )
            return vectors
        except Exception as exc:  # API errors vary by google-genai version.
            last_error = exc
            if attempt + 1 == retries:
                break
            is_quota = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            delay = min(90, (15 if is_quota else 2**attempt))
            print(f"Embedding batch failed; retrying in {delay}s ({attempt + 1}/{retries})")
            time.sleep(delay)
    raise RuntimeError("embedding batch failed after retries") from last_error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("sections"))
    parser.add_argument("--destination", type=Path, default=Path("index"))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=4)
    args = parser.parse_args()
    if args.batch_size < 1 or args.retries < 1:
        parser.error("batch-size and retries must be positive")

    load_dotenv()
    model = os.getenv("EMBED_MODEL")
    if not model:
        parser.error("EMBED_MODEL is missing from .env")
    if not os.getenv("GEMINI_API_KEY"):
        parser.error("GEMINI_API_KEY is missing from .env")

    records = load_records(args.source)
    texts = [embedding_text(record) for record in records]
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    checkpoint_vectors = args.destination / "embedding_checkpoint.npy"
    checkpoint_meta = args.destination / "embedding_checkpoint.json"
    vectors: list[list[float]] = []
    if checkpoint_vectors.exists() and checkpoint_meta.exists():
        checkpoint = json.loads(checkpoint_meta.read_text(encoding="utf-8"))
        if checkpoint.get("model") == model and checkpoint.get("record_ids") == [r["id"] for r in records]:
            vectors = np.load(checkpoint_vectors).tolist()
            print(f"Resuming from {len(vectors):,} completed embeddings")
        else:
            print("Ignoring incompatible embedding checkpoint")
    total_batches = (len(texts) + args.batch_size - 1) // args.batch_size
    start_batch = len(vectors)
    for batch_number, start in enumerate(range(start_batch, len(texts), args.batch_size), start=1):
        batch = texts[start : start + args.batch_size]
        print(f"Embedding batch {batch_number}/{total_batches} ({len(batch)} records)")
        vectors.extend(embed_batch(client, model, batch, args.retries))
        args.destination.mkdir(parents=True, exist_ok=True)
        np.save(checkpoint_vectors, np.asarray(vectors, dtype="float32"))
        checkpoint_meta.write_text(
            json.dumps({"model": model, "record_ids": [r["id"] for r in records]}),
            encoding="utf-8",
        )
        if args.delay and start + args.batch_size < len(texts):
            time.sleep(args.delay)

    matrix = np.asarray(vectors, dtype="float32")
    if matrix.ndim != 2 or matrix.shape[0] != len(records):
        raise RuntimeError(f"unexpected embedding matrix shape: {matrix.shape}")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    args.destination.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(args.destination / "sections.faiss"))
    np.save(args.destination / "vectors.npy", matrix)
    (args.destination / "records.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metadata = {
        "record_count": len(records),
        "dimensions": int(matrix.shape[1]),
        "embedding_model": model,
        "metric": "inner_product_on_L2_normalized_vectors",
        "batch_size": args.batch_size,
    }
    (args.destination / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {args.destination / 'sections.faiss'}")
    print(f"Records: {len(records):,}; dimensions: {matrix.shape[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

