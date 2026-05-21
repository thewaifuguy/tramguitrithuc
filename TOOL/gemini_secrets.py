"""Load GEMINI_API_KEY from Streamlit Secrets, env, .env, or TOML files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_ENV_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_KEY")

_TOOL_ROOT = Path(__file__).resolve().parent


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().strip('"').strip("'")
    return text or None


def _from_mapping(mapping: Any, names: tuple[str, ...]) -> str | None:
    if mapping is None:
        return None
    try:
        items = dict(mapping) if hasattr(mapping, "keys") else {}
    except Exception:
        items = {}
    for name in names:
        if name in items:
            key = _clean(items[name])
            if key:
                return key
    for val in items.values():
        if isinstance(val, dict) or hasattr(val, "keys"):
            for name in names:
                try:
                    key = _clean(val[name])  # type: ignore[index]
                    if key:
                        return key
                except (KeyError, TypeError):
                    continue
    return None


def _from_toml_files() -> str | None:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None

    candidates = (
        _TOOL_ROOT / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
        _TOOL_ROOT.parent / ".streamlit" / "secrets.toml",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            key = _from_mapping(data, _ENV_NAMES)
            if key:
                return key
        except Exception:
            continue
    return None


def resolve_gemini_api_key() -> str | None:
    """Find API key from every supported source (fresh read each call)."""
    for name in _ENV_NAMES:
        key = _clean(os.environ.get(name))
        if key:
            return key

    try:
        import streamlit as st

        key = _from_mapping(st.secrets, _ENV_NAMES)
        if key:
            return key
        for name in _ENV_NAMES:
            try:
                key = _clean(getattr(st.secrets, name))
                if key:
                    return key
            except Exception:
                continue
    except Exception:
        pass

    try:
        from dotenv import dotenv_values

        env_file = _TOOL_ROOT / ".env"
        if env_file.is_file():
            key = _from_mapping(dotenv_values(env_file), _ENV_NAMES)
            if key:
                return key
    except Exception:
        pass

    return _from_toml_files()


def inject_gemini_key_to_env() -> str | None:
    """Push resolved key into os.environ so LiteLLM/agents can read it."""
    key = resolve_gemini_api_key()
    if key:
        os.environ["GEMINI_API_KEY"] = key
    return key


def key_status() -> dict[str, str | bool]:
    key = resolve_gemini_api_key()
    if not key:
        sources: list[str] = []
        try:
            import streamlit as st

            sources = list(st.secrets.keys()) if hasattr(st.secrets, "keys") else []
        except Exception:
            sources = []
        return {
            "ok": False,
            "hint": "Chưa đọc được GEMINI_API_KEY",
            "preview": "",
            "secret_keys": ", ".join(sources[:8]) or "(trống)",
        }
    return {
        "ok": True,
        "hint": "Đã nạp key",
        "preview": f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "(ok)",
        "secret_keys": "",
    }
