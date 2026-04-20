"""Pollinations.ai wrapper — generate images from text prompts.

Pollinations serves images directly at a URL (no API key, no POST).
We just construct the URL; the image is generated on-demand when the URL
is fetched by the browser. For Day 4 (PDF export) we'll add a downloader.
"""

from __future__ import annotations

import hashlib
from urllib.parse import quote

_BASE_URL = "https://image.pollinations.ai/prompt"


def image_url(
    prompt: str,
    width: int = 768,
    height: int = 512,
    seed: int | None = None,
    nologo: bool = True,
    model: str = "flux",
) -> str:
    """Construct a Pollinations image URL. Image is generated when URL is fetched."""
    # Deterministic seed from prompt so the same prompt gives the same image
    if seed is None:
        seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % (2**31)

    # Pollinations likes raw prompts in path; URL-encode special chars
    encoded = quote(prompt, safe="")
    params = f"width={width}&height={height}&seed={seed}&model={model}"
    if nologo:
        params += "&nologo=true"
    return f"{_BASE_URL}/{encoded}?{params}"
