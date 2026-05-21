"""Cached loaders for the official sample handbook PDF (Streamlit-safe)."""

from __future__ import annotations

import streamlit as st

import config


@st.cache_data(show_spinner=False)
def get_sample_handbook_bytes() -> bytes | None:
    path = config.sample_handbook_path()
    if not path:
        return None
    return path.read_bytes()


def sample_handbook_download_name() -> str:
    return config.SAMPLE_HANDBOOK_FILENAME
