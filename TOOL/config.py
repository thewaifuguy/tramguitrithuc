"""Central config: load .env + expose model names and paths."""

from pathlib import Path

from dotenv import load_dotenv
import os

from gemini_secrets import inject_gemini_key_to_env, resolve_gemini_api_key

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

# === LLM models (LiteLLM format: provider/model-name) ===
WRITER_MODEL = "gemini/gemini-2.5-flash-lite"
MEDIA_MODEL = "gemini/gemini-2.5-flash-lite"
ANALYZER_MODEL = "gemini/gemini-2.5-flash-lite"
CRITIC_MODEL = "gemini/gemini-2.5-flash-lite"
ADVISOR_MODEL = "gemini/gemini-2.5-flash-lite"
REEL_MODEL = "gemini/gemini-2.5-flash-lite"

# === Paths ===
PROMPTS_DIR = PROJECT_ROOT / "prompts"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_DIR = PROJECT_ROOT / "data"
SQLITE_PATH = DATA_DIR / "gced.db"

ASSETS_DIR = PROJECT_ROOT / "dashboard" / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"


def sample_handbook_path() -> Path | None:
    from dashboard.sample_pdf import sample_handbook_path as _find

    return _find()


# === Generation params ===
WRITER_TEMPERATURE = 0.7
WRITER_MAX_TOKENS = 8000

# === Workflow rules ===
MAX_RETRY = 1

# === Image generation bypass ===
# Set BYPASS_IMAGE_GEN=1 in .env (or env var) to globally disable all Pollinations calls.
# In the Streamlit UI the user can also toggle this per-session from the sidebar.
import os as _os
BYPASS_IMAGE_GEN: bool = _os.getenv("BYPASS_IMAGE_GEN", "0").strip() == "1"

# === Brand ===
BRAND_NAME = "Trạm gửi tri thức"
COLOR_PRIMARY = "#2C5F5C"
COLOR_BACKGROUND = "#F5EFDC"
COLOR_ACCENT = "#E8A33D"


def gemini_api_key() -> str | None:
    return resolve_gemini_api_key()


def gemini_key_status() -> dict[str, str | bool]:
    from gemini_secrets import key_status

    return key_status()


def sync_streamlit_secrets_to_env() -> None:
    inject_gemini_key_to_env()


def require_gemini_key() -> str:
    key = inject_gemini_key_to_env()
    if not key:
        status = gemini_key_status()
        keys_hint = status.get("secret_keys", "")
        extra = f" Keys trong Secrets: [{keys_hint}]." if keys_hint else ""
        raise RuntimeError(
            "GEMINI_API_KEY chưa được nạp. "
            "Streamlit Cloud → Settings → Secrets, dán đúng:\n"
            'GEMINI_API_KEY = "your-key-here"\n'
            "Sau đó Save → Reboot app. "
            "Hoặc nhập key tạm ở sidebar (mục Cấu hình API)."
            + extra
        )
    return key
