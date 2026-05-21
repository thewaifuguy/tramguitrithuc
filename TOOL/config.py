"""Central config: load .env + expose model names and paths."""

from pathlib import Path

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent
# override=False: Streamlit Secrets / env vars win; .env only fills missing (local dev)
load_dotenv(PROJECT_ROOT / ".env", override=False)

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
CRITIC_MODEL = "gemini/gemini-2.5-flash-lite"
ADVISOR_MODEL = "gemini/gemini-2.5-flash-lite"
REEL_MODEL = "gemini/gemini-2.5-flash-lite"

# === API keys ===
def _clean_key(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    return cleaned or None


def sync_streamlit_secrets_to_env() -> None:
    """Copy Streamlit Cloud / local secrets into os.environ (call once at app startup)."""
    try:
        import streamlit as st

        for name in ("GEMINI_API_KEY",):
            try:
                if name in st.secrets:
                    val = _clean_key(st.secrets[name])
                    if val:
                        os.environ[name] = val
            except Exception:
                continue
    except Exception:
        pass


def _resolve_gemini_api_key() -> str | None:
    """Streamlit Secrets → environment → .env (via load_dotenv)."""
    sync_streamlit_secrets_to_env()

    key: str | None = None

    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            try:
                key = _clean_key(st.secrets["GEMINI_API_KEY"])
            except (KeyError, TypeError):
                pass
    except Exception:
        pass

    if not key:
        key = _clean_key(os.getenv("GEMINI_API_KEY"))

    return key


def gemini_api_key() -> str | None:
    return _resolve_gemini_api_key()


def gemini_key_status() -> dict[str, str | bool]:
    """Safe diagnostic for UI (never exposes full key)."""
    key = _resolve_gemini_api_key()
    if not key:
        return {"ok": False, "hint": "Chưa có GEMINI_API_KEY", "preview": ""}
    return {
        "ok": True,
        "hint": "Đã nạp key",
        "preview": f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "(key ngắn)",
    }


def __getattr__(name: str):
    if name == "GEMINI_API_KEY":
        return _resolve_gemini_api_key()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# === Paths ===
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_DIR = PROJECT_ROOT / "data"
SQLITE_PATH = DATA_DIR / "gced.db"

ASSETS_DIR = PROJECT_ROOT / "dashboard" / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

# === Sample handbook (demo / presentation fallback) ===
SAMPLE_HANDBOOK_FILENAME = "TRẠM_GỬI_TRI_THỨC_-_ĐÁNH_THỨC_TƯ_DUY.pdf"
SAMPLE_HANDBOOK_TITLE = "Trạm gửi tri thức - Đánh thức tư duy"
SAMPLE_HANDBOOK_PATH = PROJECT_ROOT / SAMPLE_HANDBOOK_FILENAME


def sample_handbook_path() -> Path | None:
    """Return path to the official sample handbook PDF if present."""
    return SAMPLE_HANDBOOK_PATH if SAMPLE_HANDBOOK_PATH.is_file() else None

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
    key = _resolve_gemini_api_key()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. "
            "Streamlit Cloud: App settings → Secrets → GEMINI_API_KEY = \"your-key\". "
            "Local: copy .env.example to .env. Get a key at https://aistudio.google.com/"
        )
    return key
