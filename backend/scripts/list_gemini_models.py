"""List Gemini models actually available to this API key.

Usage:
    python -m scripts.list_gemini_models
"""

from __future__ import annotations

from google import genai

from app.core.config import settings


def main() -> None:
    client = genai.Client(api_key=settings.google_api_key)
    print("Models supporting generateContent (usable for chat/drafting):\n")
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" in actions:
            print(f"  {m.name}")

    print("\nModels supporting embedContent (usable for embeddings):\n")
    for m in client.models.list():
        actions = getattr(m, "supported_actions", None) or []
        if "embedContent" in actions:
            print(f"  {m.name}")


if __name__ == "__main__":
    main()