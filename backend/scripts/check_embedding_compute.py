"""Week-1 checklist: is BGE-M3 fast enough on this machine?

Run this before the schema's vector(1024) becomes load-bearing. If throughput
here is unusable, switch EMBEDDING_MODEL to BAAI/bge-small-en-v1.5,
EMBEDDING_DIM to 384, and change every vector(1024) in the migration to
vector(384) -- same embedding family, lighter model, hybrid-RAG design intact.

    python -m scripts.check_embedding_compute
"""

from __future__ import annotations

import time

from app.core.config import settings
from app.services.embeddings import embed_texts, get_model

SAMPLE = (
    "The organisation conducted 42 community health camps across 12 villages in "
    "Maharashtra during FY 2024-25, reaching 3,180 beneficiaries, of whom 68 percent "
    "were women and adolescent girls. Programme expenditure for the year was "
    "INR 24.6 lakh against a sanctioned budget of INR 26 lakh."
)


def main() -> None:
    print(f"model      : {settings.embedding_model}")
    print(f"device set : {settings.embedding_device}")

    t0 = time.perf_counter()
    model = get_model()
    load_s = time.perf_counter() - t0
    print(f"load time  : {load_s:.1f}s")
    print(f"device used: {model.device}")

    for n in (1, 8, 32):
        texts = [SAMPLE] * n
        t0 = time.perf_counter()
        vectors = embed_texts(texts, batch_size=8)
        elapsed = time.perf_counter() - t0
        print(
            f"batch {n:>3}  : {elapsed:6.2f}s  ({n / elapsed:5.1f} chunks/s)  dim={len(vectors[0])}"
        )

    dim = len(embed_texts([SAMPLE])[0])
    if dim != settings.embedding_dim:
        print(
            f"\nMISMATCH: model produces {dim}-dim vectors but "
            f"EMBEDDING_DIM={settings.embedding_dim}."
            "\nFix the env var AND the vector(...) columns in the migration before ingesting."
        )
    else:
        print(f"\nOK: {dim}-dim vectors match EMBEDDING_DIM and the schema.")

    print(
        "\nRule of thumb: a 40-page annual report is ~300 chunks. Under ~5 chunks/s "
        "the ingestion pipeline will be painful -- consider bge-small."
    )


if __name__ == "__main__":
    main()
