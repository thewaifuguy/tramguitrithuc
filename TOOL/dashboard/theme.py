"""Brand theme helpers: CSS injection + hero + how-it-works + CTA card + sidebar."""

from __future__ import annotations

import base64
import mimetypes

import streamlit as st

import config
from db import storage as fs
from db.schemas import ChapterStatus

_STYLE_PATH = config.ASSETS_DIR / "style.css"


def _find_logo() -> tuple[bytes, str] | None:
    """Look for any logo.* file in assets dir, return (bytes, mime) or None."""
    if not config.ASSETS_DIR.exists():
        return None
    for path in config.ASSETS_DIR.iterdir():
        if path.stem.lower() == "logo" and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            mime, _ = mimetypes.guess_type(path.name)
            return path.read_bytes(), mime or "image/png"
    return None


def apply_theme() -> None:
    """Inject custom CSS. Call once at top of each page."""
    if _STYLE_PATH.exists():
        css = _STYLE_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_hero() -> None:
    """Render branded hero with logo + tagline + live stats."""
    logo_html = _logo_html()
    stats = _get_stats()

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-left">
                {logo_html}
                <div class="hero-text">
                    <div class="hero-title">{config.BRAND_NAME}</div>
                    <div class="hero-tagline">
                        Dự án giáo dục phi lợi nhuận · AI biên soạn handbook phương pháp học
                    </div>
                    <span class="hero-badge">🌱 Đang phát triển</span>
                </div>
            </div>
            <div class="hero-stats">
                <div class="hero-stat">
                    <div class="hero-stat-icon">⏳</div>
                    <div class="hero-stat-value">{stats['pending']}</div>
                    <div class="hero-stat-label">Chờ duyệt</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-icon">✅</div>
                    <div class="hero-stat-value">{stats['approved']}</div>
                    <div class="hero-stat-label">Đã duyệt</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-icon">📚</div>
                    <div class="hero-stat-value">{stats['total']}</div>
                    <div class="hero-stat-label">Tổng chapter</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Branded sidebar with mission + impact goal + system info."""
    stats = _get_stats()
    target_books = 12
    target_students = 1000
    progress_pct = min(100, int((stats["approved"] / target_books) * 100))

    with st.sidebar:
        st.markdown("### 🎯 Sứ mệnh")
        st.markdown(
            "Dùng AI để biên soạn handbook phương pháp học cho học sinh cấp 2. "
            "Lợi nhuận in sách tặng học sinh có hoàn cảnh khó khăn."
        )

        st.markdown("### 📈 Mục tiêu 2026")
        st.markdown(
            f"""
            <div style="background:rgba(245,239,220,0.1);padding:12px;border-radius:10px;border-left:3px solid #E8A33D;">
                <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;">
                    <span>Handbook xuất bản</span>
                    <strong>{stats["approved"]} / {target_books}</strong>
                </div>
                <div style="background:rgba(0,0,0,0.2);height:6px;border-radius:3px;overflow:hidden;">
                    <div style="background:#E8A33D;height:100%;width:{progress_pct}%;border-radius:3px;"></div>
                </div>
                <div style="font-size:12px;margin-top:10px;opacity:0.85;">
                    🎓 {target_students}+ học sinh khó khăn được hỗ trợ
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🤖 Hệ thống")
        st.markdown(
            f"""
            **Writer Agent** · `{config.WRITER_MODEL.split('/')[-1]}`

            AI sinh draft → con người duyệt → publish.
            Tối đa {config.MAX_RETRY + 1} lần thử / chapter.
            """
        )

        st.caption("Demo v0.3 — 2026-04-16")


def render_how_it_works() -> None:
    """3-step pipeline visual under hero."""
    st.markdown(
        """
        <div class="how-it-works">
            <div class="step-card">
                <div class="step-num">1</div>
                <div class="step-icon">✍️</div>
                <div class="step-title">Writer AI viết</div>
                <div class="step-desc">Sinh chapter handbook với cấu trúc, ví dụ thực tế và bài tập áp dụng cho học sinh.</div>
            </div>
            <div class="step-arrow">→</div>
            <div class="step-card">
                <div class="step-num">2</div>
                <div class="step-icon">👁️</div>
                <div class="step-title">Người duyệt</div>
                <div class="step-desc">Bạn review chất lượng, đảm bảo nội dung đúng và phù hợp với học sinh Việt Nam.</div>
            </div>
            <div class="step-arrow">→</div>
            <div class="step-card">
                <div class="step-num">3</div>
                <div class="step-icon">📱</div>
                <div class="step-title">Media AI marketing</div>
                <div class="step-desc">Sinh post Facebook, hình ảnh và xuất bản đến phụ huynh tự động.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cta_header() -> None:
    """CTA header only (without chips — chips are a separate section)."""
    st.markdown(
        """
        <div class="cta-standalone">
            <div class="cta-title">✨ Bắt đầu với một chapter mới</div>
            <div class="cta-subtitle">AI sẽ viết draft trong khoảng 30-60 giây. Nhập chủ đề riêng hoặc chọn một gợi ý bên dưới.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_suggestion_bar(suggestions: list[str]) -> str | None:
    """Separate chip bar with label + resuggest button. Returns clicked topic or None."""
    st.markdown(
        """
        <div class="suggestion-header">
            <span class="suggestion-label">💡 Gợi ý chủ đề</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Chips row + resuggest button
    cols = st.columns([*[3] * len(suggestions), 1])
    chosen: str | None = None
    for col, s in zip(cols[:-1], suggestions):
        if col.button(s, key=f"chip-{s}", use_container_width=True):
            chosen = s
    with cols[-1]:
        if st.button("🎲 Làm mới", key="resuggest", use_container_width=True, help="Đề xuất bộ gợi ý khác"):
            st.session_state["_resuggest"] = True
            st.rerun()
    return chosen


def render_empty_state(title: str, description: str, cta: str = "") -> None:
    """Friendly empty state with illustration."""
    cta_html = (
        f'<div class="empty-cta">{cta}</div>' if cta else ""
    )
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-illustration">📭</div>
            <div class="empty-title">{title}</div>
            <div class="empty-desc">{description}</div>
            {cta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sample_card() -> None:
    """Promotional card + download for the official sample handbook PDF."""
    sample_path = config.sample_handbook_path()
    st.markdown(
        f"""
        <div class="sample-card">
            <div class="sample-icon">📖</div>
            <div class="sample-text">
                <div class="sample-title">Handbook mẫu: {config.SAMPLE_HANDBOOK_TITLE}</div>
                <div class="sample-desc">PDF in được, có ảnh minh họa, layout sách chuyên nghiệp — dùng cho demo và thuyết trình.</div>
            </div>
            <div class="sample-badge">Mẫu chính thức</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if sample_path:
        with open(sample_path, "rb") as f:
            st.download_button(
                label="⬇️ Tải handbook mẫu (PDF)",
                data=f.read(),
                file_name=config.SAMPLE_HANDBOOK_FILENAME,
                mime="application/pdf",
                use_container_width=True,
                key="download-sample-handbook",
                help=f"Bản thiết kế đã hoàn thiện: {config.SAMPLE_HANDBOOK_TITLE}",
            )
    else:
        st.caption(
            f"⚠️ Chưa có file `{config.SAMPLE_HANDBOOK_FILENAME}` trong thư mục TOOL. "
            "Copy PDF handbook mẫu vào đó để hiển thị nút tải."
        )


def _get_stats() -> dict[str, int]:
    try:
        pending = len(fs.list_by_status(ChapterStatus.PENDING, limit=999))
        approved = len(fs.list_by_status(ChapterStatus.APPROVED, limit=999))
        rejected = len(fs.list_by_status(ChapterStatus.REJECTED, limit=999))
        escalated = len(fs.list_by_status(ChapterStatus.ESCALATED, limit=999))
    except Exception:
        return {"pending": 0, "approved": 0, "total": 0}
    return {
        "pending": pending,
        "approved": approved,
        "total": pending + approved + rejected + escalated,
    }


def _logo_html() -> str:
    found = _find_logo()
    if found is None:
        return '<div class="hero-fallback">📚</div>'
    data, mime = found
    encoded = base64.b64encode(data).decode()
    return f'<img class="hero-logo" src="data:{mime};base64,{encoded}" alt="logo" />'
