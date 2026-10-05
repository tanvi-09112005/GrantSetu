"""Seed the three synthetic sample NGOs through the REAL registration flow.

For each NGO in data/sample_ngos/synthetic_pack/ this script:

  1. creates a confirmed login in Supabase Auth (admin API, so no email is sent)
  2. signs in to get a session token
  3. calls POST /ngo/register  (the same endpoint the wizard uses) with the
     Darpan, 12A and 80G certificates
  4. fills in mission / sectors / registration numbers on the profile
  5. uploads the remaining PDFs (FCRA, CSR-1, financials, impact reports)
  6. uploads the logo, stamp and signature PNGs

It is safe to re-run: anything already present is skipped.

Run from the backend/ folder, with the backend server already running
(uvicorn app.main:app --reload) and your .env filled in:

    python -m scripts.seed_sample_ngos --email-base you@gmail.com
    python -m scripts.seed_sample_ngos --email-base you@gmail.com --only pragati-gram-vikas
    python -m scripts.seed_sample_ngos --email-base you@gmail.com --dry-run

Logins become you+pragati@gmail.com, you+shiksha@gmail.com, you+arogya@gmail.com
(Gmail delivers all "+" aliases to your own inbox).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from app.core.config import settings

PACK = Path(__file__).resolve().parents[2] / "data" / "sample_ngos" / "synthetic_pack"
# Registration already stores these three; everything else is uploaded afterwards.
REGISTRATION_DOCS = {"darpan_certificate": "darpan_certificate", "cert_12a": "cert_12a", "cert_80g": "cert_80g"}
TIMEOUT_DOC = 900  # first upload loads the embedding model - be patient


def die(msg: str) -> None:
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_manifests(only: str | None) -> list[tuple[Path, dict]]:
    out = []
    for manifest in sorted(PACK.glob("0*/ngo.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if only and data["slug"] != only:
            continue
        out.append((manifest.parent, data))
    if not out:
        die(f"No NGO found in {PACK}" + (f" matching --only {only}" if only else "") +
            ". Run generate_pack.py first.")
    return out


# --------------------------------------------------------------------------- supabase
def supa_headers(key: str, token: str | None = None) -> dict:
    return {"apikey": key, "Authorization": f"Bearer {token or key}", "Content-Type": "application/json"}


def ensure_user(email: str, password: str, name: str) -> None:
    """Create a confirmed user via the admin API (idempotent)."""
    if not settings.supabase_service_role_key:
        die("SUPABASE_SERVICE_ROLE_KEY is missing from backend/.env")
    r = requests.post(
        f"{settings.supabase_url}/auth/v1/admin/users",
        headers=supa_headers(settings.supabase_service_role_key),
        json={"email": email, "password": password, "email_confirm": True,
              "user_metadata": {"full_name": name}},
        timeout=30,
    )
    if r.status_code in (200, 201):
        print(f"   created login {email}")
    elif r.status_code == 422 and "already" in r.text.lower():
        print(f"   login {email} already exists")
    else:
        die(f"Could not create user {email}: {r.status_code} {r.text}")


def sign_in(email: str, password: str) -> str:
    key = settings.supabase_anon_key or settings.supabase_service_role_key
    r = requests.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        headers=supa_headers(key), json={"email": email, "password": password}, timeout=30,
    )
    if r.status_code != 200:
        die(f"Sign-in failed for {email}: {r.status_code} {r.text}\n"
            "(If this login existed already, it may have a different password: use --password.)")
    return r.json()["access_token"]


# --------------------------------------------------------------------------- api
class Api:
    def __init__(self, base: str, token: str):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"

    def call(self, method: str, path: str, **kw):
        kw.setdefault("timeout", 120)
        r = self.s.request(method, self.base + path, **kw)
        if r.status_code >= 400:
            detail = r.text
            try:
                detail = r.json().get("detail", detail)
            except ValueError:
                pass
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {detail}")
        return r.json() if r.content and r.headers.get("content-type", "").startswith("application/json") else None


def seed_one(folder: Path, m: dict, api_base: str, email: str, password: str, dry: bool) -> dict:
    print(f"\n=== {m['ngo_name']}  ({m['darpan_id']}) ===")
    files = {k: folder / v for k, v in m["documents"].items()}
    brand = {k: folder / v for k, v in m["branding"].items()}
    missing = [str(p) for p in [*files.values(), *brand.values()] if not p.exists()]
    if missing:
        die("Missing pack files:\n  " + "\n  ".join(missing))
    if dry:
        print(f"   [dry-run] would use login {email}; {len(files)} PDFs + {len(brand)} images OK")
        return {"email": email, "password": password, "ngo": m["ngo_name"]}

    ensure_user(email, password, m["admin_name"])
    api = Api(api_base, sign_in(email, password))

    # --- 3. register (skipped if this login already has an NGO)
    existing = api.call("GET", "/ngo/profile")
    if existing:
        ngo_id = existing[0]["id"]
        print("   NGO already registered - reusing it")
    else:
        handles = {k: files[k].open("rb") for k in REGISTRATION_DOCS}
        try:
            res = api.call(
                "POST", "/ngo/register", timeout=TIMEOUT_DOC,
                data={
                    "admin_name": m["admin_name"], "admin_designation": m["admin_designation"],
                    "admin_phone": m["admin_phone"], "ngo_name": m["ngo_name"],
                    "incorporation_year": m["incorporation_year"], "state": m["state"],
                    "district": m["district"], "darpan_id": m["darpan_id"],
                    "has_12a": str(m["has_12a"]).lower(), "has_80g": str(m["has_80g"]).lower(),
                    "has_fcra": str(m["has_fcra"]).lower(),
                },
                files={
                    "darpan_certificate": (files["darpan_certificate"].name, handles["darpan_certificate"], "application/pdf"),
                    "cert_12a": (files["cert_12a"].name, handles["cert_12a"], "application/pdf"),
                    "cert_80g": (files["cert_80g"].name, handles["cert_80g"], "application/pdf"),
                },
            )
        finally:
            for h in handles.values():
                h.close()
        ngo_id = res["ngo_id"]
        print(f"   registered -> verification_status = {res['verification_status']}")

    # --- 4. complete the profile (mission, sectors, real registration numbers)
    cur = api.call("GET", f"/ngo/profile/{ngo_id}")
    p = m["profile"]
    api.call("PUT", f"/ngo/profile/{ngo_id}", json={
        "name": cur["name"], "location": cur.get("location"), "darpan_id": cur.get("darpan_id"),
        "mission": p["mission"], "sectors": p["sectors"], "registered_on": p["registered_on"],
        "reg_12a": p["reg_12a"], "reg_80g": p["reg_80g"], "reg_fcra": p["reg_fcra"],
        "fcra_status": p["fcra_status"], "fcra_valid_until": p["fcra_valid_until"],
        "fcra_verified_on": cur.get("fcra_verified_on"),
    })
    print("   profile completed (mission, sectors, registration numbers)")

    # --- 5. remaining PDFs
    have = {d["doc_type"] for d in api.call("GET", "/ngo/documents", params={"ngo_id": ngo_id})}
    for doc_type, path in files.items():
        if doc_type in have:
            print(f"   - {doc_type}: already in vault")
            continue
        with path.open("rb") as fh:
            out = api.call("POST", "/ngo/documents", timeout=TIMEOUT_DOC,
                           data={"ngo_id": ngo_id, "doc_type": doc_type},
                           files={"file": (path.name, fh, "application/pdf")})
        print(f"   + {doc_type}: {out['ingest_status']} ({out.get('chunk_count', 0)} chunks)")

    # --- 6. branding images
    have_assets = {a["asset_type"] for a in api.call("GET", "/ngo/assets", params={"ngo_id": ngo_id})}
    for asset_type, path in brand.items():
        if asset_type in have_assets:
            print(f"   - {asset_type}: already uploaded")
            continue
        with path.open("rb") as fh:
            api.call("PUT", f"/ngo/assets/{asset_type}", data={"ngo_id": ngo_id},
                     files={"file": (path.name, fh, "image/png")})
        print(f"   + {asset_type} image uploaded")

    return {"email": email, "password": password, "ngo": m["ngo_name"]}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email-base", required=True, help="your real email, e.g. you@gmail.com (aliases are derived)")
    ap.add_argument("--password", default="Demo@12345", help="password for the three sample logins")
    ap.add_argument("--api", default="http://127.0.0.1:8000", help="backend base URL")
    ap.add_argument("--only", help="seed just one NGO by slug, e.g. pragati-gram-vikas")
    ap.add_argument("--dry-run", action="store_true", help="check files and print the plan, change nothing")
    args = ap.parse_args()

    if "@" not in args.email_base:
        die("--email-base must be a full email address")
    local, domain = args.email_base.split("@", 1)

    if not args.dry_run:
        if not settings.supabase_url:
            die("SUPABASE_URL is missing from backend/.env")
        try:
            requests.get(args.api.rstrip("/") + "/health", timeout=10).raise_for_status()
        except Exception as exc:  # noqa: BLE001
            die(f"Backend not reachable at {args.api} ({exc}).\nStart it first: uvicorn app.main:app --reload")

    results = []
    for folder, m in load_manifests(args.only):
        email = f"{local}+{m['email_local']}@{domain}"
        try:
            results.append(seed_one(folder, m, args.api, email, args.password, args.dry_run))
        except RuntimeError as exc:
            die(f"{m['ngo_name']}: {exc}")

    print("\n" + "=" * 60)
    print("Sample accounts ready. Sign in to the app with:")
    for r in results:
        print(f"  {r['email']}   /  {r['password']}    ({r['ngo']})")


if __name__ == "__main__":
    main()
