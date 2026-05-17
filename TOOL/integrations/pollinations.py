"""Pollinations.ai wrapper — generate images from text prompts.

Pollinations serves images directly at a URL (no API key, no POST).
We just construct the URL; the image is generated on-demand when the URL
is fetched by the browser. For Day 4 (PDF export) we'll add a downloader.
"""

from pathlib import Path
from typing import Optional
from urllib.parse import quote
import hashlib

_BASE_URL = "https://image.pollinations.ai/prompt"


def image_url(
    prompt: str,
    width: int = 768,
    height: int = 512,
    seed: Optional[int] = None,
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

def download_image(url: str, target_path: Path) -> bool:
    """Fetch image from Pollinations and save to disk."""
    import requests
    try:
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            target_path.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False

