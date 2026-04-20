"""Central config: load .env + expose model names and paths."""

from pathlib import Path

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent
# override=True: .env thắng biến môi trường hệ thống (tránh key cũ bị cache)
load_dotenv(PROJECT_ROOT / ".env", override=True)

# === LLM models (LiteLLM format: provider/model-name) ===
# NOTE: Gemini 2.5 Pro no longer has free tier (Google removed it).
# Gemini free tier: 1500 requests/day per model. If hit daily quota,
# switch WRITER_MODEL to a different model (each has separate quota pool):
#   - "gemini/gemini-2.5-flash"     (highest quality Flash)
#   - "gemini/gemini-2.5-flash-lite"     (stable, reliable, separate quota)
#   - "gemini/gemini-1.5-flash"     (older, smaller usage, separate quota)
#   - "gemini/gemini-2.5-flash-lite"  (smallest, separate quota)
WRITER_MODEL = "gemini/gemini-2.5-flash-lite"
MEDIA_MODEL = "gemini/gemini-2.5-flash-lite"
ANALYZER_MODEL = "gemini/gemini-2.5-flash-lite"

# === API keys ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Paths ===
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_DIR = PROJECT_ROOT / "data"
SQLITE_PATH = DATA_DIR / "gced.db"

ASSETS_DIR = PROJECT_ROOT / "dashboard" / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

# === Generation params ===
WRITER_TEMPERATURE = 0.7
WRITER_MAX_TOKENS = 8000

# === Workflow rules ===
MAX_RETRY = 1  # demo: 1 retry max (production was 3)

# === Brand ===
BRAND_NAME = "Trạm gửi tri thức"
COLOR_PRIMARY = "#2C5F5C"
COLOR_BACKGROUND = "#F5EFDC"
COLOR_ACCENT = "#E8A33D"


def require_gemini_key() -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Copy .env.example to .env and fill in your key "
            "from https://aistudio.google.com/"
        )
    return GEMINI_API_KEY
