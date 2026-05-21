"""Sample handbook PDF — self-contained (no config.py dependency)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_TOOL_ROOT = Path(__file__).resolve().parent.parent
_ASSETS_DIR = _TOOL_ROOT / "dashboard" / "assets"

SAMPLE_HANDBOOK_TITLE = "Trạm gửi tri thức - Đánh thức tư duy"
SAMPLE_HANDBOOK_FILENAME = "TRẠM_GỬI_TRI_THỨC_-_ĐÁNH_THỨC_TƯ_DUY.pdf"
SAMPLE_HANDBOOK_FILENAME_ASCII = "sample_handbook.pdf"


def sample_handbook_path() -> Path | None:
    """Find the official sample handbook on disk (Unicode or ASCII name)."""
    candidates = (
        _TOOL_ROOT / SAMPLE_HANDBOOK_FILENAME,
        _TOOL_ROOT / SAMPLE_HANDBOOK_FILENAME_ASCII,
        _ASSETS_DIR / SAMPLE_HANDBOOK_FILENAME_ASCII,
        _ASSETS_DIR / SAMPLE_HANDBOOK_FILENAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    try:
        for path in sorted(_TOOL_ROOT.glob("*.pdf")):
            if path.stat().st_size > 500_000:
                return path
    except OSError:
        pass
    return None


@st.cache_data(show_spinner=False)
def get_sample_handbook_bytes() -> bytes | None:
    path = sample_handbook_path()
    if not path:
        return None
    return path.read_bytes()


def sample_handbook_download_name() -> str:
    path = sample_handbook_path()
    if path:
        return path.name
    return SAMPLE_HANDBOOK_FILENAME_ASCII
