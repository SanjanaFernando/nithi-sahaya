"""Build a Gemini embedding and FAISS index from Phase 2 section records.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --batch-size 25 --delay 1
"""

from __future__ import annotations

import argparse
import hashlib
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


def records_fingerprint(records: list[dict]) -> str:
    payload = "\n".join(f"{r['id']}\0{embedding_text(r)}" for r in records)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_checkpoint(destination: Path, model: str, records: list[dict], completed: dict[int, list[float]]) -> None:
    indices = sorted(completed)
    np.save(
        destination / "embedding_checkpoint.npy",
        np.asarray([completed[index] for index in indices], dtype="float32"),
    )
    (destination / "embedding_checkpoint.json").write_text(
        json.dumps({
            "model": model,
            "record_ids": [records[index]["id"] for index in indices],
            "completed_indices": indices,
            "total_records": len(records),
            "content_fingerprint": records_fingerprint(records),
        }),
        encoding="utf-8",
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
            error_text = str(exc)
            if "per day" in error_text.lower() or "PerDay" in error_text:
                raise RuntimeError(
                    "Gemini's daily embedding quota is exhausted. The checkpoint is saved; "
                    "rerun this command after the quota resets."
                ) from exc
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
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="reuse compatible saved vectors and write a resumable checkpoint without API calls",
    )
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
    args.destination.mkdir(parents=True, exist_ok=True)
    checkpoint_vectors = args.destination / "embedding_checkpoint.npy"
    checkpoint_meta = args.destination / "embedding_checkpoint.json"
    completed: dict[int, list[float]] = {}
    record_index = {record["id"]: index for index, record in enumerate(records)}

    # Reuse only vectors whose complete embedded text is unchanged.
    old_records_path = args.destination / "records.json"
    old_vectors_path = args.destination / "vectors.npy"
    if old_records_path.exists() and old_vectors_path.exists():
        old_records = json.loads(old_records_path.read_text(encoding="utf-8"))
        # Load and close the file instead of keeping a read-only memory map.
        # On Windows, replacing vectors.npy while its mmap is still open fails
        # with OSError: [Errno 22] Invalid argument.
        old_vectors = np.load(old_vectors_path)
        old_by_text = {
            embedding_text(record): old_vectors[index]
            for index, record in enumerate(old_records)
            if index < len(old_vectors)
        }
        for index, record in enumerate(records):
            vector = old_by_text.get(texts[index])
            if vector is not None:
                completed[index] = np.asarray(vector, dtype="float32").tolist()

    if checkpoint_vectors.exists() and checkpoint_meta.exists():
        checkpoint = json.loads(checkpoint_meta.read_text(encoding="utf-8"))
        if checkpoint.get("model") == model:
            saved_vectors = np.load(checkpoint_vectors)
            saved_ids = checkpoint.get("record_ids", [])
            saved_indices = checkpoint.get("completed_indices")
            if saved_indices is None:
                # Backward compatibility with the original prefix checkpoint.
                saved_indices = list(range(len(saved_vectors)))
                saved_ids = saved_ids[:len(saved_vectors)]
            current_fingerprint = records_fingerprint(records)
            exact_checkpoint = checkpoint.get("content_fingerprint") == current_fingerprint
            for row, (saved_index, record_id) in enumerate(zip(saved_indices, saved_ids)):
                target = record_index.get(record_id)
                if target is None or row >= len(saved_vectors):
                    continue
                unchanged = exact_checkpoint or checkpoint.get("content_fingerprint") is None
                # Only exclude this record from a legacy, un-fingerprinted partial
                # checkpoint. A full fingerprint match proves its saved vector is
                # for the current text and must be reused.
                legacy_changed_record = (
                    checkpoint.get("content_fingerprint") is None
                    and record_id == "ch01_industrial_disputes_act_s31c"
                )
                if unchanged and not legacy_changed_record:
                    completed[target] = np.asarray(saved_vectors[row], dtype="float32").tolist()
            print(f"Reused {len(completed):,} exact or checkpointed embeddings")
        else:
            print("Ignoring incompatible embedding checkpoint")

    missing = [index for index in range(len(texts)) if index not in completed]
    save_checkpoint(args.destination, model, records, completed)
    if args.prepare_only:
        print(f"Prepared {len(completed):,} vectors; {len(missing):,} require API embeddings")
        return 0

    total_batches = (len(missing) + args.batch_size - 1) // args.batch_size
    for batch_number, offset in enumerate(range(0, len(missing), args.batch_size), start=1):
        positions = missing[offset : offset + args.batch_size]
        batch = [texts[index] for index in positions]
        print(f"Embedding batch {batch_number}/{total_batches} ({len(batch)} records)")
        batch_vectors = embed_batch(client, model, batch, args.retries)
        completed.update({index: vector for index, vector in zip(positions, batch_vectors)})
        save_checkpoint(args.destination, model, records, completed)
        if args.delay and batch_number < total_batches:
            time.sleep(args.delay)

    if len(completed) != len(records):
        raise RuntimeError(f"only {len(completed)} of {len(records)} embeddings are available")
    matrix = np.asarray([completed[index] for index in range(len(records))], dtype="float32")
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

