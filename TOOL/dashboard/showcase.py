"""Fast showcase pipeline for live presentations (no API, no PDF build)."""

from __future__ import annotations

import time
from datetime import datetime

import streamlit as st

from db.schemas import ChapterDraft, ChapterStatus, PostDraft, PostStatus, PostType


SHOWCASE_STEP_SEC = 0.35


def ensure_demo_seeded(fs) -> None:
    """Pre-load demo chapters + posts once per session."""
    if st.session_state.get("demo_seeded"):
        return
    try:
        if fs.list_by_status(ChapterStatus.APPROVED, limit=1):
            st.session_state["demo_seeded"] = True
            return
    except Exception:
        pass
    from scripts.seed_demo_data import seed

    seed()
    st.session_state["demo_seeded"] = True


def _mock_posts(draft_id: str, topic: str) -> list[PostDraft]:
    return [
        PostDraft(
            chapter_id=draft_id,
            type=PostType.SHORT,
            content=(
                f"📚 Mới từ Trạm gửi tri thức: {topic[:80]} — "
                "phương pháp học dễ áp dụng cho học sinh cấp 2. #TramGuiTriThuc #GCED"
            ),
            status=PostStatus.APPROVED,
        ),
        PostDraft(
            chapter_id=draft_id,
            type=PostType.INFORMATIVE,
            content=(
                "3 bước bắt đầu ngay hôm nay:\n"
                "1. Chọn 1 kỹ năng\n2. Học 25 phút\n3. Ôn lại 5 phút\n"
                "Handbook miễn phí cho bạn bè vùng cao."
            ),
            status=PostStatus.APPROVED,
        ),
    ]


def run_fast_showcase(
    fs,
    topic: str,
    *,
    demo_data: list[dict],
    get_pdf_bytes,
    pdf_download_name: str,
    handbook_title: str,
) -> None:
    """
    End-to-end visual pipeline in ~10–15 seconds.
    No Gemini, no Pollinations, no PDF generation.
    """
    ensure_demo_seeded(fs)

    status_area = st.empty()
    progress_bar = st.progress(0)
    item = demo_data[0]
    display_topic = topic.strip() or item["topic"]

    status_area.info(f"🚀 **Bước 1/4:** AI Writer — *{display_topic}*")
    progress_bar.progress(15)
    time.sleep(SHOWCASE_STEP_SEC)

    draft_obj = ChapterDraft(
        topic=display_topic,
        content_md=item["content_md"],
        image_prompts=item.get("image_prompts", []),
        status=ChapterStatus.PENDING,
    )
    draft_id = fs.save_draft(draft_obj)
    st.success(f"✅ Chapter sẵn sàng (showcase). ID: `{draft_id}`")

    status_area.info("🔍 **Bước 2/4:** AI Critic phê duyệt...")
    progress_bar.progress(40)
    time.sleep(SHOWCASE_STEP_SEC)
    fs.update_status(draft_id, ChapterStatus.APPROVED)
    st.success("✅ Đã phê duyệt (Quality Passed).")

    status_area.info("📱 **Bước 3/4:** AI Media — bài Facebook...")
    progress_bar.progress(65)
    time.sleep(SHOWCASE_STEP_SEC)

    existing = fs.list_posts_by_chapter(draft_id)
    if not existing:
        for p in _mock_posts(draft_id, display_topic):
            fs.save_post(p)
        post_count = 2
    else:
        post_count = len(existing)

    st.success(f"✅ {post_count} bài quảng bá sẵn sàng.")

    status_area.info("📄 **Bước 4/4:** Xuất bản Handbook PDF...")
    progress_bar.progress(85)
    time.sleep(SHOWCASE_STEP_SEC)

    pdf_bytes = get_pdf_bytes()
    if not pdf_bytes:
        st.error("Thiếu file sample_handbook.pdf trên server — push PDF lên GitHub.")
        return

    progress_bar.progress(100)
    status_area.success("🎊 **SHOWCASE HOÀN TẤT** (~15 giây)")
    st.balloons()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"#### 📖 {handbook_title}")
        st.download_button(
            label="⬇️ Tải Handbook",
            data=pdf_bytes,
            file_name=pdf_download_name,
            mime="application/pdf",
            use_container_width=True,
            key="showcase-download-handbook",
        )
    with col2:
        st.markdown("#### 📱 Social")
        st.success("Xem tab **Quảng bá (Social)** để preview bài viết.")

    st.caption("Chế độ Showcase: dùng dữ liệu + PDF mẫu có sẵn — không gọi API.")
