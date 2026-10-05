"""Backend gate: only document-matched NGOs may use grant matching / proposals."""

from __future__ import annotations

from fastapi import HTTPException, status

VERIFIED_STATUSES = ("document_matched", "verified")

NOT_VERIFIED_MESSAGE = (
    "Your NGO isn't verified yet. Upload your Darpan certificate on the Vault or "
    "Profile page to unlock grant matching and proposals."
)


def is_verified(profile: dict | None) -> bool:
    if not profile:
        return False
    # Shared demo / sample profiles are not user accounts (no owner): always usable.
    if profile.get("user_id") is None:
        return True
    return profile.get("verification_status") in VERIFIED_STATUSES


def ensure_verified(profile: dict | None) -> None:
    """Raise 403 unless ``profile`` (a row from ngo_profiles) is verified.

    ``None`` is allowed through: the route's own "not found" handling decides.
    """
    if profile is None:
        return
    if not is_verified(profile):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NOT_VERIFIED_MESSAGE)
