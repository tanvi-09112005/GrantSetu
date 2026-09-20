"""Sync sample NGO profiles into the database so they have valid DB UUIDs for documents and proposals."""

import json
from pathlib import Path
from app.db import pool

def sync():
    user = pool.fetch_one("select id from auth.users limit 1")
    if not user:
        print("No user found in auth.users")
        return
    user_id = user["id"]
    
    json_path = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "sample_profiles.json"
    if not json_path.exists():
        print("sample_profiles.json not found")
        return

    profiles = json.loads(json_path.read_text(encoding="utf-8"))
    for p in profiles:
        existing = pool.fetch_one("select id from ngo_profiles where name = %s", (p["name"],))
        if existing:
            print(f"Already exists: {p['name']} -> {existing['id']}")
            continue
        
        row = pool.fetch_one(
            """
            insert into ngo_profiles
                (user_id, name, mission, sectors, location,
                 reg_12a, reg_80g, reg_fcra, darpan_id,
                 fcra_valid_until, fcra_status, registered_on)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            returning id, name
            """,
            (
                user_id,
                p["name"],
                p.get("mission"),
                p.get("sectors", []),
                p.get("location"),
                p.get("reg_12a"),
                p.get("reg_80g"),
                p.get("reg_fcra"),
                p.get("darpan_id"),
                p.get("fcra_valid_until"),
                p.get("fcra_status", "unknown"),
                p.get("registered_on"),
            ),
        )
        print(f"Created: {row['name']} -> {row['id']}")

if __name__ == "__main__":
    sync()
