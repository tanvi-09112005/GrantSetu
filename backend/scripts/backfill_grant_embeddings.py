"""Backfill embeddings for grants where embedding is NULL."""

import time
from app.db import pool
from app.services.embeddings import embed_texts

def backfill():
    rows = pool.fetch_all("select id, title, funder_name, description, sectors from grants where embedding is null order by id")
    print(f"Found {len(rows)} grants missing embeddings.")
    if not rows:
        return

    batch_size = 16
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = []
        for r in batch:
            sectors = ", ".join(r["sectors"]) if r.get("sectors") else ""
            t = f"{r['title']}. {r['funder_name']}. {r.get('description', '')}. Sectors: {sectors}."
            texts.append(t)
        
        vectors = embed_texts(texts)
        for r, vec in zip(batch, vectors):
            pool.execute("update grants set embedding = %s where id = %s", (vec, r["id"]))
        
        print(f"Embedded & updated {min(i + batch_size, len(rows))}/{len(rows)} grants.")
        time.sleep(0.5)

    count = pool.fetch_one("select count(*) as c from grants where embedding is not null")["c"]
    print(f"Total grants with embeddings now: {count}")

if __name__ == "__main__":
    backfill()
