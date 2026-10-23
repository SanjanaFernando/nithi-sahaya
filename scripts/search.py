"""Search the Phase 4 FAISS index with Gemini query embeddings."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import faiss
from dotenv import load_dotenv
from google import genai


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--index", type=Path, default=Path("index"))
    args = parser.parse_args()
    if args.k < 1:
        parser.error("k must be positive")

    load_dotenv()
    model = os.getenv("EMBED_MODEL")
    if not model or not os.getenv("GEMINI_API_KEY"):
        parser.error("GEMINI_API_KEY and EMBED_MODEL must be configured in .env")

    index = faiss.read_index(str(args.index / "sections.faiss"))
    records = json.loads((args.index / "records.json").read_text(encoding="utf-8"))
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.embed_content(model=model, contents=[args.question])
    query = response.embeddings[0].values
    import numpy as np

    vector = np.asarray([query], dtype="float32")
    faiss.normalize_L2(vector)
    scores, indices = index.search(vector, min(args.k, len(records)))
    for rank, (score, position) in enumerate(zip(scores[0], indices[0]), start=1):
        record = records[int(position)]
        print(f"{rank}. score={score:.4f} {record['act_name']} s.{record['section_number']}")
        print(f"   {record.get('heading', '')}")
        print(f"   {record['source_file']} page {record['source_page']}")
        print(f"   {record['text'][:300].replace(chr(10), ' ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

