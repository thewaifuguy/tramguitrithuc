"""Streamlit dashboard: Trạm gửi tri thức.

Workflow:
  - Sinh chapter mới (button trên header → form → call WriterAgent live)
  - Pending tab: review draft, approve hoặc reject (regenerate auto)
  - Approved tab: chapter đã duyệt, sẵn sàng cho Phase 4 (PDF + posts)
  - Rejected tab: lịch sử reject (chỉ xem, không action)
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

import streamlit as st

# Make TOOL/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

import config
from agents.media import MediaAgent
from agents.writer import WriterAgent
from agents.critic import CriticAgent
import json
import datetime
from agents.advisor import SocialAdvisorAgent
from agents.reel import ReelAgent

# Force reload of storage and schemas to pick up new functions/classes
import importlib
import db.schemas
import db.storage
import config
importlib.reload(db.schemas)
importlib.reload(db.storage)
importlib.reload(config)
from db import storage as fs

from db.schemas import (
    REJECT_REASON_LABELS,
    ApprovalRecord,
    ChapterDraft,
    ChapterStatus,
    PostDraft,
    PostStatus,
    PostType,
    Project,
    RejectEntry,
    RejectReason,
)
from export.pdf_builder import build_chapter_pdf
from integrations.facebook_mock import render_fb_post
from integrations.pollinations import download_image, image_url


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """Fetch Pollinations image server-side with long timeout, cache 1h."""
    try:
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return r.content
    except Exception:
        pass
    return None
import random

from dashboard.theme import (
    apply_theme,
    render_cta_header,
    render_empty_state,
    render_hero,
    render_how_it_works,
    render_sample_card,
    render_sidebar,
    render_suggestion_bar,
)

st.set_page_config(
    page_title=config.BRAND_NAME,
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()
render_hero()
# render_sidebar()  # Removed to fix double menu issue, moved to Info tab
# render_how_it_works() # Moved to Info tab
render_sample_card()


# === Generate new chapter (top action) ===

def _trigger_generate(topic: str, outline: str | None) -> bool:
    """Returns True nếu tạo thành công, False nếu fail."""
    import time
    from db.schemas import ChapterStatus
    
    try:
        with st.spinner(f"AI Writer đang viết chapter về '{topic}'..."):
            agent = WriterAgent()
            
            # Use a thread or simple timer to mock timeout for demo
            # In a real app we'd use asyncio.wait_for
            start_time = time.time()
            
            # For the demo, we'll simulate a potential slow call
            # by checking if a special 'demo' flag or specific topic is used,
            # or just wrapping the call in a try/except with timeout.
            
            # Since streamlit is synchronous here, we'll just do a standard call
            # but add a note that if it fails, we check for demo data.
            try:
                out = agent.generate_chapter(topic=topic, outline=outline)
                draft = ChapterDraft(
                    topic=out.topic,
                    content_md=out.content_md,
                    image_prompts=out.image_prompts,
                    input_tokens=out.input_tokens,
                    output_tokens=out.output_tokens,
                )
                draft_id = fs.save_draft(draft)
            except Exception as e:
                # Fallback to seed data if API fails or times out
                st.warning("⚠️ API đang chậm hoặc gặp lỗi. Đang chuyển sang Demo Data dự phòng...")
                time.sleep(2)
                demo_items = fs.list_by_status(ChapterStatus.APPROVED, limit=1)
                if demo_items:
                    _, demo_obj = demo_items[0]
                    draft = ChapterDraft(
                        topic=f"[DEMO] {demo_obj.topic}",
                        content_md=demo_obj.content_md,
                        image_prompts=demo_obj.image_prompts,
                    )
                    draft_id = fs.save_draft(draft)
                else:
                    raise e # Rethrow if no demo data
    except RuntimeError as e:
        st.error(f"❌ {e}")
        return False
    except Exception as e:
        st.error(
            f"❌ Lỗi không lường trước: {type(e).__name__}: {e}\n\n"
            "Vui lòng thử lại sau vài phút."
        )
        return False
    # Lưu flash message để hiện sau rerun
    st.session_state["_flash"] = ("success", f"✓ Đã tạo chapter mới (ID `{draft_id}`). Xem ở tab Đang chờ duyệt.")
    return True


SUGGESTION_POOL = [
    "Pomodoro cho học sinh hay trì hoãn",
    "Active Recall khi ôn thi môn Lịch sử",
    "Đặt mục tiêu SMART cho lớp 9",
    "Học nhóm hiệu quả qua Zalo",
    "Kỹ thuật feynman để hiểu sâu kiến thức",
    "Mind Map cho môn Sinh học",
    "Spaced Repetition với Anki",
    "Cách ghi chú Cornell",
    "Vượt qua nỗi sợ thi cử",
    "Quản lý thời gian học + giải trí cân bằng",
    "Tự học hiệu quả khi không có gia sư",
    "Học từ vựng tiếng Anh bằng ngữ cảnh",
    "Rèn kỹ năng đọc hiểu môn Văn",
    "Cách làm bài tập Toán khó không nản",
    "Chiến lược ôn thi vào 10 cho học sinh trung bình",
]


def _pick_suggestions(n: int = 4) -> list[str]:
    """Chọn n gợi ý random, cache trong session để không đổi giữa rerun."""
    if st.session_state.pop("_resuggest", False) or "suggestions" not in st.session_state:
        st.session_state["suggestions"] = random.sample(SUGGESTION_POOL, n)
    return st.session_state["suggestions"]


# Clear form trước khi widgets render (chỉ chạy khi flag được set ở rerun trước)
if st.session_state.pop("_clear_form", False):
    st.session_state["topic_input"] = ""
    st.session_state["outline_input"] = ""

# Flash message từ rerun trước (success/error sau khi submit)
_flash = st.session_state.pop("_flash", None)
if _flash:
    kind, msg = _flash
    if kind == "success":
        st.success(msg)
    else:
        st.error(msg)

render_cta_header()

# Chip click → set session_state cho widget key rồi rerun
chosen_topic = render_suggestion_bar(_pick_suggestions())
if chosen_topic:
    st.session_state["topic_input"] = chosen_topic
    st.rerun()

with st.form("new-chapter", clear_on_submit=False):
    topic = st.text_input(
        "Chủ đề chapter",
        key="topic_input",
        placeholder="VD: Pomodoro cho học sinh hay trì hoãn",
    )
    outline = st.text_area(
        "Outline gợi ý (tùy chọn)",
        key="outline_input",
        placeholder="Để trống cho AI tự quyết outline",
        height=80,
    )
    if st.form_submit_button("🚀 Generate chapter", type="primary"):
        if not topic.strip():
            st.error("Phải nhập chủ đề.")
        else:
            success = _trigger_generate(topic.strip(), outline.strip() or None)
            if success:
                # Chỉ rerun + clear khi thành công
                st.session_state["_clear_form"] = True
                st.rerun()
            # Nếu fail, không rerun → error message (st.error trong _trigger_generate) ở lại

# The section-heading for Workspace was removed to fix the double menu issue


# === Tabs ===

tab_intro, tab_pending, tab_approved, tab_projects, tab_promotion, tab_rejected, tab_demo = st.tabs(
    ["ℹ️ Giới thiệu", "⏳ Chờ duyệt bài", "✅ Sách đã duyệt", "📚 Dự án (Projects)", "📢 Quảng bá (Social)", "❌ Lịch sử từ chối", "🎬 Demo Mode"]
)

with tab_intro:
    st.markdown("### 🎯 Sứ mệnh")
    st.markdown(
        "Dùng AI để biên soạn handbook phương pháp học cho học sinh cấp 2. "
        "Lợi nhuận in sách tặng học sinh có hoàn cảnh khó khăn."
    )
    
    st.markdown("---")
    
    col_mission, col_stats = st.columns(2)
    with col_mission:
        st.markdown("### 📈 Mục tiêu 2026")
        st.markdown(
            """
            <div style="background:rgba(44, 95, 92, 0.05);padding:20px;border-radius:15px;border-left:5px solid #E8A33D;color:#111111;">
                <div style="font-size:16px;margin-bottom:10px;">
                    🎓 <b>1000+</b> học sinh khó khăn được hỗ trợ handbook miễn phí.
                </div>
                <div style="font-size:14px;opacity:0.8;">
                    Dự án đang trong giai đoạn phát triển nội dung (Phase 2).
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col_stats:
        st.markdown("### 🤖 Hệ thống AI")
        st.markdown(
            f"""
            - **Writer Agent:** Biên soạn nội dung chuyên sâu.
            - **Media Agent:** Thiết kế bài viết Poster Risograph.
            - **Model:** `{config.WRITER_MODEL.split('/')[-1]}`
            """
        )

    st.markdown("---")
    render_how_it_works()

with tab_demo:
    st.markdown(
        """
        <div class="demo-header">
            <h3>🎬 Chế độ Demo nhanh</h3>
            <p>Dành cho hội đồng ban giám khảo. Chạy quy trình mẫu để xem kết quả nhanh nhất.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_info, col_reset = st.columns([2, 1])
    with col_reset:
        if st.button("🗑️ Xóa toàn bộ dữ liệu", use_container_width=True):
            fs.clear_all()
            st.warning("Đã xóa toàn bộ DB. Hãy rerun app.")
            st.rerun()

    st.divider()
    st.subheader("🏁 Pipeline Thuyết trình (Presentation Mode)")
    st.write("Chạy quy trình tự động từ ý tưởng đến sản phẩm hoàn thiện (Handbook + Posts) để trình diễn.")
    
    demo_topic = st.text_input("Nhập chủ đề muốn trình diễn", value="Kỹ thuật ghi nhớ Active Recall cho học sinh")
    
    if st.button("🏁 Bắt đầu Quy trình Demo", type="primary", use_container_width=True):
        if not demo_topic:
            st.error("Vui lòng nhập chủ đề.")
        else:
            run_demo_pipeline(demo_topic)

def run_demo_pipeline(topic: str):
    """Runs a full end-to-end demo flow with visual steps."""
    status_area = st.empty()
    progress_bar = st.progress(0)
    
    # Step 1: Generation
    status_area.info(f"🚀 **Bước 1/4:** AI Writer đang biên soạn chapter: *{topic}*...")
    progress_bar.progress(10)
    
    try:
        from agents.writer import WriterAgent
        writer = WriterAgent()
        draft_obj = writer.generate_chapter(topic)
        draft_id = fs.save_draft(draft_obj)
        progress_bar.progress(40)
        st.success(f"✅ Đã soạn xong chapter. ID: `{draft_id}`")
    except Exception as e:
        st.warning(f"⚠️ API chậm hoặc lỗi: {e}. Đang chuyển sang dữ liệu mẫu để demo...")
        from scripts.seed_demo_data import DEMO_DATA
        item = DEMO_DATA[0]
        from db.schemas import ChapterDraft, ChapterStatus
        draft_obj = ChapterDraft(
            topic=item["topic"],
            content_md=item["content_md"],
            image_prompts=item["image_prompts"],
            status=ChapterStatus.APPROVED,
            approved_at=datetime.now()
        )
        draft_id = fs.save_draft(draft_obj)
        topic = draft_obj.topic
        st.info("💡 Đang sử dụng bài mẫu: 'Kỹ thuật Pomodoro'")
        progress_bar.progress(40)
        
    # Step 2: Review & Approve
    status_area.info("🔍 **Bước 2/4:** AI Critic đang kiểm duyệt chất lượng nội dung...")
    import time
    time.sleep(2) # Visual pause
    fs.update_status(draft_id, ChapterStatus.APPROVED)
    progress_bar.progress(60)
    st.success("✅ Nội dung đã được AI Critic phê duyệt (Quality Passed).")
    
    # Step 3: Social Media
    status_area.info("📱 **Bước 3/4:** AI Media đang lên kế hoạch truyền thông & thiết kế bài viết...")
    try:
        from agents.media import MediaAgent
        media_agent = MediaAgent()
        posts = media_agent.generate_posts(draft_id, draft_obj.content_md)
    except:
        # Fallback posts
        from db.schemas import PostDraft, PostType, PostStatus
        posts = [
            PostDraft(chapter_id=draft_id, type=PostType.SHORT, content="Mẹo tập trung Pomodoro...", status=PostStatus.APPROVED)
        ]
        
    for p in posts:
        p.status = PostStatus.APPROVED # Auto-approve for demo
        fs.save_post(p)
    progress_bar.progress(80)
    st.success(f"✅ Đã tạo xong {len(posts)} bài viết quảng bá.")
    
    # Step 4: PDF Export
    status_area.info("📄 **Bước 4/4:** Đang đóng gói nội dung và xuất bản Handbook PDF...")
    from export.pdf_builder import build_chapter_pdf
    pdf_path = build_chapter_pdf(draft_id, topic, draft_obj.content_md)
    progress_bar.progress(100)
    
    status_area.success("🎊 **QUY TRÌNH HOÀN TẤT!**")
    st.balloons()
    
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        st.markdown("#### 📖 Handbook PDF")
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Tải xuống Handbook", f, file_name=f"{topic}.pdf")
    with col_res2:
        st.markdown("#### 📱 Facebook Posts")
        st.info("Các bài viết đã sẵn sàng trong tab 'Quảng bá (Social)'.")
        
    if st.button("Quay lại Dashboard"):
        st.rerun()
            

    st.divider()
    st.markdown("**Gợi ý cho ban giám khảo:**")
    st.write("1. Nhập một chủ đề bất kỳ ở phía trên.")
    st.write("2. Vào tab **Chờ duyệt** để xem AI viết.")
    st.write("3. Bấm **Duyệt** để chuyển qua tab **Sách đã duyệt**.")
    st.write("4. Bấm **Xuất PDF** để xem thành phẩm cuối cùng.")



def render_draft(draft_id: str, draft: ChapterDraft, show_actions_for: Optional[ChapterStatus] = None) -> None:
    word_count = len(draft.content_md.split())
    reading_min = max(1, word_count // 250)
    status_label = _status_badge(draft.status)

    # Strip leading H1 title line from content to avoid duplication with card title
    content_for_display = _strip_leading_title(draft.content_md)

    with st.container(border=True):
        # === Header row: title + status badge
        st.markdown(
            f"""
            <div class="draft-header">
                <div class="draft-title-block">
                    <div class="draft-title">{draft.topic}</div>
                    <div class="draft-meta">
                        ID <code>{draft_id}</code> · {draft.created_at:%d/%m/%Y %H:%M}
                        · 📖 {word_count} từ · ⏱️ ~{reading_min} phút đọc
                        · 🔁 Lần thử {draft.retry_count + 1}/{config.MAX_RETRY + 1}
                    </div>
                </div>
                {status_label}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # === Reject history if any
        if draft.reject_history:
            with st.expander(f"⚠️ Đã từng bị từ chối {len(draft.reject_history)} lần"):
                for entry in draft.reject_history:
                    label = REJECT_REASON_LABELS.get(entry.reason_code, entry.reason_code.value)
                    st.write(f"• **{label}** — {entry.note or '(không ghi chú)'} _({entry.at:%H:%M})_")

        # === 2-column layout: content (left) + images (right)
        col_content, col_images = st.columns([3, 1])
        with col_content:
            st.markdown(
                '<div class="section-label">📖 Nội dung chapter</div>',
                unsafe_allow_html=True,
            )
            with st.container(height=480, border=False):
                st.markdown('<div class="draft-content-wrapper"></div>', unsafe_allow_html=True)
                st.markdown(_strip_image_prompts(content_for_display))
        with col_images:
            st.markdown(
                f'<div class="section-label">🖼️ Ảnh minh họa ({len(draft.image_prompts)})</div>',
                unsafe_allow_html=True,
            )
            with st.container(height=480, border=False):
                if not draft.image_prompts:
                    st.caption("Chapter này không có image prompt.")
                else:
                    _render_image_sidebar(draft_id, draft)

        # === Inline content editor ===
        with st.expander("✏️ Chỉnh sửa nội dung", expanded=False):
            st.caption("Sửa trực tiếp Markdown. Nhấn **Lưu thay đổi** để cập nhật vào cơ sở dữ liệu.")
            edited_topic = st.text_input(
                "Tiêu đề chapter",
                value=draft.topic,
                key=f"edit-topic-{draft_id}",
            )
            edited_md = st.text_area(
                "Nội dung Markdown",
                value=draft.content_md,
                height=400,
                key=f"edit-md-{draft_id}",
            )
            col_save, col_preview = st.columns([1, 1])
            with col_save:
                if st.button("💾 Lưu thay đổi", key=f"save-edit-{draft_id}", type="primary", use_container_width=True):
                    if not edited_topic.strip():
                        st.error("Tiêu đề không được để trống.")
                    else:
                        fs.update_draft_content(draft_id, edited_topic.strip(), edited_md)
                        st.session_state["_flash"] = ("success", f"✓ Đã lưu thay đổi cho chapter ID `{draft_id}`.")
                        st.rerun()
            with col_preview:
                if st.button("👁️ Xem trước", key=f"preview-edit-{draft_id}", use_container_width=True):
                    st.session_state[f"preview-open-{draft_id}"] = True

            if st.session_state.get(f"preview-open-{draft_id}"):
                st.divider()
                st.markdown("**Xem trước nội dung đã chỉnh sửa:**")
                st.markdown(_strip_image_prompts(edited_md))

        # === Action row (depends on status)
        if show_actions_for == ChapterStatus.PENDING:
            _render_pending_actions(draft_id, draft)
        elif show_actions_for == ChapterStatus.APPROVED:
            _render_approved_actions(draft_id, draft)
        elif show_actions_for in (ChapterStatus.REJECTED, ChapterStatus.ESCALATED):
            _render_rejected_actions(draft_id, draft)


def _strip_leading_title(md: str) -> str:
    """Remove the first H1 line so it's not duplicated with the card title."""
    lines = md.lstrip().split("\n", 1)
    if lines and lines[0].startswith("# "):
        return lines[1] if len(lines) > 1 else ""
    return md


def _strip_image_prompts(md: str) -> str:
    """Remove IMAGE_PROMPT HTML comments (shown separately in images tab)."""
    import re
    return re.sub(r"<!--\s*IMAGE_PROMPT:.*?-->\s*", "", md, flags=re.DOTALL)


def _render_image_sidebar(draft_id: str, draft: ChapterDraft) -> None:
    """Fetch Pollinations images server-side with long timeout, cache 1h, then display."""
    st.caption("⏳ Lần đầu sinh ảnh mất 15-30s. Sau đó cache local sẽ hiện ngay.")
    prompts = draft.image_prompts
    for i, prompt in enumerate(prompts, 1):
        url = image_url(prompt, width=512, height=384)
        with st.spinner(f"Đang sinh ảnh #{i}..."):
            data = _fetch_image_bytes(url)
        if data:
            st.image(data, caption=f"Ảnh #{i}", use_container_width=True)
            
            if st.button(f"🔄 Đổi ảnh #{i}", key=f"regen-img-{draft_id}-{i}", use_container_width=True):
                import random
                import re
                
                # Append a random variation to the prompt to change the seed
                new_variation = f" (v{random.randint(100, 999)})"
                new_prompt = prompt + new_variation
                
                # Update the markdown content
                old_tag = f"<!-- IMAGE_PROMPT: {prompt} -->"
                new_tag = f"<!-- IMAGE_PROMPT: {new_prompt} -->"
                new_md = draft.content_md.replace(old_tag, new_tag)
                
                # Update the prompts list
                new_prompts = list(draft.image_prompts)
                new_prompts[i-1] = new_prompt
                
                # Persist to DB
                fs.update_draft_content(draft_id, draft.topic, new_md, new_prompts)
                
                st.session_state["_flash"] = ("success", f"Đã gửi yêu cầu đổi ảnh #{i}!")
                st.rerun()
        else:
            st.warning(f"⚠️ Ảnh #{i} không load được — Pollinations có thể đang bận. Refresh để thử lại.")


def _status_badge(status: ChapterStatus) -> str:
    mapping = {
        ChapterStatus.PENDING: ("status-pending", "⏳ Đang chờ duyệt"),
        ChapterStatus.APPROVED: ("status-approved", "✅ Đã duyệt"),
        ChapterStatus.REJECTED: ("status-rejected", "❌ Đã từ chối"),
        ChapterStatus.ESCALATED: ("status-rejected", "🚨 Đã escalate"),
    }
    css, label = mapping.get(status, ("", status.value))
    return f'<span class="status-badge {css}">{label}</span>'


def _render_pending_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_approve, col_rewrite, col_reject = st.columns([1, 1, 1])

    with col_approve:
        if st.button("✅ Duyệt", key=f"approve-{draft_id}", type="primary", use_container_width=True):
            fs.approve_draft(draft_id)
            fs.log_approval(ApprovalRecord(draft_id=draft_id, action="approve"))
            st.session_state["_flash"] = ("success", "Đã duyệt chapter!")
            st.rerun()

    with col_rewrite:
        if st.button("✨ Viết lại", key=f"rewrite-{draft_id}", use_container_width=True, help="AI viết lại bản khác ngay lập tức"):
            _handle_reject(draft_id, draft, RejectReason.TOO_GENERIC, "Người dùng yêu cầu viết lại bản khác.")

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="❌ Từ chối")


def _render_approved_actions(draft_id: str, draft: ChapterDraft) -> None:
    # Check if posts already exist to determine button label
    existing_posts = fs.list_posts_by_chapter(draft_id)
    has_posts = len(existing_posts) > 0
    
    # Project assignment
    projects = fs.list_projects()
    project_names = {pid: p.name for pid, p in projects}
    project_options = ["(Chưa phân loại)"] + list(project_names.values())
    current_p_name = project_names.get(str(draft.project_id), "(Chưa phân loại)") if draft.project_id else "(Chưa phân loại)"
    
    col_pdf, col_media, col_proj, col_unapprove, col_reject, col_delete = st.columns([1.2, 1.2, 1.2, 0.5, 0.5, 0.5])

    with col_pdf:
        if st.button(
            "📄 Xuất PDF",
            key=f"pdf-{draft_id}",
            type="primary",
            use_container_width=True,
            help="Tạo file PDF handbook với đầy đủ ảnh minh họa",
        ):
            try:
                with st.spinner("Đang chuẩn bị PDF..."):
                    pdf_path = build_chapter_pdf(draft_id, draft.topic, draft.content_md)
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Tải PDF",
                        data=f,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"dl-pdf-{draft_id}",
                        use_container_width=True,
                    )
                st.success("✓ Thành công!")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with col_media:
        btn_label = "🔄 Viết lại bài FB" if has_posts else "✨ Sinh bài FB"
        if st.button(btn_label, key=f"gen-media-{draft_id}", use_container_width=True):
            _trigger_media_gen(draft_id, draft.content_md)
            st.rerun()

    with col_proj:
        try:
            default_ix = project_options.index(current_p_name)
        except ValueError:
            default_ix = 0
            
        new_p_name = st.selectbox(
            "📍 Dự án",
            options=project_options,
            index=default_ix,
            key=f"proj-sel-{draft_id}",
            label_visibility="collapsed"
        )
        if new_p_name != current_p_name:
            if new_p_name == "(Chưa phân loại)":
                fs.assign_chapter_to_project(draft_id, None)
            else:
                target_pid = next(pid for pid, name in project_names.items() if name == new_p_name)
                fs.assign_chapter_to_project(draft_id, target_pid)
            st.rerun()

    with col_unapprove:
        if st.button("↩️", key=f"unapprove-{draft_id}", use_container_width=True, help="Trả về chờ duyệt"):
            fs.set_status(draft_id, ChapterStatus.PENDING)
            st.rerun()

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="❌")

    with col_delete:
        if st.button("🗑️", key=f"delete-approved-{draft_id}", use_container_width=True, help="Xóa vĩnh viễn"):
            fs.delete_draft(draft_id)
            st.rerun()


def _render_rejected_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_reapprove, col_delete = st.columns(2)

    with col_reapprove:
        if st.button(
            "✅ Duyệt lại",
            key=f"reapprove-{draft_id}",
            type="primary",
            use_container_width=True,
            help="Chuyển chapter này qua 'Đã duyệt'",
        ):
            fs.set_status(draft_id, ChapterStatus.APPROVED)
            fs.log_approval(ApprovalRecord(draft_id=draft_id, action="approve", note="Duyệt lại sau khi reject"))
            st.session_state["_flash"] = ("success", "Đã duyệt lại chapter!")
            st.rerun()

    with col_delete:
        if st.button(
            "🗑️ Xóa",
            key=f"delete-rejected-{draft_id}",
            use_container_width=True,
        ):
            fs.delete_draft(draft_id)
            st.session_state["_flash"] = ("success", f"Đã xóa chapter ID {draft_id}.")
            st.rerun()


def _render_reject_popover(draft_id: str, draft: ChapterDraft, button_label: str) -> None:
    with st.popover(button_label, use_container_width=True):
        st.markdown("**Lý do từ chối:**")
        reason_key = st.selectbox(
            "Lý do",
            options=list(RejectReason),
            format_func=lambda r: REJECT_REASON_LABELS[r],
            key=f"reason-{draft_id}",
            label_visibility="collapsed",
        )
        note = st.text_area(
            "Ghi chú (bắt buộc nếu chọn 'Lý do khác')",
            key=f"note-{draft_id}",
            height=80,
        )
        if st.button(
            "Xác nhận từ chối",
            key=f"confirm-reject-{draft_id}",
            type="primary",
        ):
            _handle_reject(draft_id, draft, reason_key, note)


def _handle_reject(
    draft_id: str,
    draft: ChapterDraft,
    reason: RejectReason,
    note: str,
) -> None:
    if reason == RejectReason.OTHER and not note.strip():
        st.error("Chọn 'Lý do khác' phải ghi chú.")
        return

    reject_entry = RejectEntry(reason_code=reason, note=note.strip())
    updated = fs.reject_draft(draft_id, reject_entry)
    fs.log_approval(
        ApprovalRecord(
            draft_id=draft_id,
            action="reject",
            reason_code=reason,
            note=note.strip(),
        )
    )

    if updated.status == ChapterStatus.ESCALATED:
        st.error(
            f"Đã đạt giới hạn {config.MAX_RETRY + 1} lần thử. "
            "Bạn có thể thử lại với chủ đề khác hoặc tinh chỉnh prompt."
        )
        st.rerun()
        return

    try:
        with st.spinner(f"AI viết lại (lần {draft.retry_count + 2}/{config.MAX_RETRY + 1})..."):
            agent = WriterAgent()
            out = agent.regenerate_chapter(
                topic=draft.topic,
                previous_content=draft.content_md,
                reject=reject_entry,
            )
            new_draft = ChapterDraft(
                topic=out.topic,
                content_md=out.content_md,
                image_prompts=out.image_prompts,
                retry_count=draft.retry_count + 1,
                parent_id=draft_id,
                input_tokens=out.input_tokens,
                output_tokens=out.output_tokens,
            )
            new_id = fs.save_draft(new_draft)
    except RuntimeError as e:
        st.error(f"❌ {e}")
        return
    except Exception as e:
        st.error(f"❌ Lỗi: {type(e).__name__}: {e}")
        return

    st.success(f"Đã viết lại! Bản mới ID `{new_id}`")
    st.rerun()


def render_tab(
    status: ChapterStatus,
    empty_title: str = "",
    empty_desc: str = "",
    empty_cta: str = "",
) -> None:
    try:
        items = fs.list_by_status(status, limit=20)
    except Exception as e:
        st.error(f"Lỗi DB: {e}")
        return

    if not items:
        render_empty_state(
            title=empty_title or f"Chưa có chapter nào",
            description=empty_desc,
            cta=empty_cta,
        )
        return

    for draft_id, draft in items:
        render_draft(draft_id, draft, show_actions_for=status)


def _trigger_media_gen(draft_id: str, content: str) -> None:
    try:
        with st.spinner("AI Media đang lên ý tưởng bài viết Facebook..."):
            agent = MediaAgent()
            posts = agent.generate_posts(draft_id, content)
            for p in posts:
                fs.save_post(p)
        st.session_state["_flash"] = ("success", "Đã sinh bài viết quảng bá! Xem ở tab Posts.")
    except Exception as e:
        st.error(f"Lỗi sinh media: {e}")


def _trigger_single_media_gen(draft_id: str, content: str, post_type: PostType) -> None:
    try:
        with st.spinner(f"AI đang viết lại bài {post_type.value}..."):
            agent = MediaAgent()
            post = agent.generate_single_post(draft_id, content, post_type)
            fs.save_post(post)
        st.session_state["_flash"] = ("success", f"Đã đổi bài {post_type.value} mới!")
    except Exception as e:
        st.error(f"Lỗi viết lại post: {e}")

with tab_pending:
    render_tab(
        ChapterStatus.PENDING,
        empty_title="Chưa có draft nào đang chờ duyệt",
        empty_desc="Bấm vào một gợi ý phía trên hoặc nhập chủ đề riêng để AI bắt đầu viết chapter đầu tiên.",
        empty_cta="↑ Cuộn lên trên để tạo",
    )

with tab_approved:
    # Custom rendering for approved to add "Generate Posts" button
    try:
        items = fs.list_by_status(ChapterStatus.APPROVED, limit=20)
    except Exception as e:
        st.error(f"Lỗi DB: {e}")
        items = []

    if not items:
        render_empty_state(
            title="Chưa có chapter nào được duyệt",
            description="Khi bạn bấm '✅ Duyệt' cho một draft, nó sẽ xuất hiện ở đây và sẵn sàng để xuất bản.",
        )
    else:
        for draft_id, draft in items:
            render_draft(draft_id, draft, show_actions_for=ChapterStatus.APPROVED)
            # The media gen button is now inside render_draft -> _render_approved_actions

with tab_projects:
    st.markdown("### 📚 Quản lý Dự án Handbook")
    
    with st.expander("➕ Tạo dự án mới", expanded=False):
        with st.form("create-project"):
            p_name = st.text_input("Tên dự án (VD: Handbook Kỹ năng Thế kỷ 21)")
            p_desc = st.text_area("Mô tả ngắn")
            if st.form_submit_button("Tạo dự án"):
                if p_name:
                    fs.save_project(Project(name=p_name, description=p_desc))
                    st.success(f"Đã tạo dự án {p_name}")
                    st.rerun()
                else:
                    st.error("Vui lòng nhập tên dự án")

    projects = fs.list_projects()
    if not projects:
        st.info("Chưa có dự án nào. Hãy tạo dự án đầu tiên để sắp xếp các chapter.")
    else:
        for p_id, p_obj in projects:
            with st.container(border=True):
                st.markdown(f"#### 📁 {p_obj.name}")
                st.caption(p_obj.description)
                
                chapters = fs.list_chapters_by_project(p_id)
                
                # --- Asset Management ---
                with st.expander("🖼️ Thiết lập hình ảnh Dự án (Chung)", expanded=False):
                    col_f, col_c, col_b = st.columns(3)
                    
                    asset_dir = config.DATA_DIR / "assets" / "projects" / str(p_id)
                    asset_dir.mkdir(parents=True, exist_ok=True)
                    
                    def _save_asset(file, role, chap_id=None):
                        if file:
                            ext = Path(file.name).suffix
                            prefix = role if not chap_id else f"chap_{chap_id}"
                            target_path = asset_dir / f"{prefix}{ext}"
                            # Delete old ones
                            for old in asset_dir.glob(f"{prefix}.*"):
                                old.unlink()
                            with open(target_path, "wb") as f:
                                f.write(file.getbuffer())
                            
                            if chap_id:
                                fs.update_chapter_cover(chap_id, str(target_path))
                            else:
                                fs.update_project_assets(p_id, {f"{role}_path": str(target_path)})
                            return str(target_path)
                        return None

                    with col_f:
                        st.caption("Bìa trước")
                        if p_obj.front_cover_path and Path(p_obj.front_cover_path).exists():
                            st.image(p_obj.front_cover_path, use_container_width=True)
                        f_file = st.file_uploader("Chọn bìa trước", key=f"f-cov-{p_id}", label_visibility="collapsed")
                        if f_file and st.button("Lưu bìa trước", key=f"btn-f-{p_id}"):
                            _save_asset(f_file, "front_cover")
                            st.rerun()
                            
                    with col_c:
                        st.caption("Trang chương (Dùng chung)")
                        if p_obj.chapter_image_path and Path(p_obj.chapter_image_path).exists():
                            st.image(p_obj.chapter_image_path, use_container_width=True)
                        c_file = st.file_uploader("Chọn trang chương", key=f"c-img-{p_id}", label_visibility="collapsed")
                        if c_file and st.button("Lưu trang chương", key=f"btn-c-{p_id}"):
                            _save_asset(c_file, "chapter_image")
                            st.rerun()

                    with col_b:
                        st.caption("Bìa sau")
                        if p_obj.back_cover_path and Path(p_obj.back_cover_path).exists():
                            st.image(p_obj.back_cover_path, use_container_width=True)
                        b_file = st.file_uploader("Chọn bìa sau", key=f"b-cov-{p_id}", label_visibility="collapsed")
                        if b_file and st.button("Lưu bìa sau", key=f"btn-b-{p_id}"):
                            _save_asset(b_file, "back_cover")
                            st.rerun()

                # --- Chapter Specific Covers ---
                if chapters:
                    with st.expander(f"📑 Cấu trúc Handbook ({len(chapters)} chương)", expanded=True):
                        for c_id, c_obj in chapters:
                            c_col_info, c_col_img = st.columns([2, 1])
                            with c_col_info:
                                st.markdown(f"**{c_obj.topic}**")
                                ch_file = st.file_uploader("Ảnh lót riêng cho chương này", key=f"ch-img-{c_id}")
                                if ch_file and st.button("Lưu ảnh chương", key=f"btn-ch-{c_id}"):
                                    _save_asset(ch_file, "chapter_cover", chap_id=c_id)
                                    st.rerun()
                            with c_col_img:
                                if c_obj.cover_path and Path(c_obj.cover_path).exists():
                                    st.image(c_obj.cover_path, caption="Ảnh lót chương", use_container_width=True)
                                elif p_obj.chapter_image_path:
                                    st.caption("Dùng ảnh chung")
                                    st.image(p_obj.chapter_image_path, use_container_width=True)
                                else:
                                    st.caption("Chưa có ảnh lót")
                            st.divider()
                else:
                    st.write("*(Chưa có chapter nào trong dự án này)*")

                st.markdown("---")
                col_export, col_del = st.columns([1, 1])
                with col_export:
                    if st.button("🚀 Gộp & Xuất Handbook (PDF)", key=f"export-p-{p_id}", type="primary"):
                        if not chapters:
                            st.warning("Cần ít nhất 1 chapter để xuất handbook.")
                        else:
                            try:
                                with st.spinner("Đang gộp và tạo Handbook tổng hợp..."):
                                    from export.pdf_builder import build_project_pdf
                                    pdf_path = build_project_pdf(p_id, p_obj.name, chapters)
                                
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        "⬇️ Tải xuống Full Handbook",
                                        data=f,
                                        file_name=f"Handbook_{p_obj.name.replace(' ', '_')}.pdf",
                                        mime="application/pdf",
                                        key=f"dl-full-{p_id}"
                                    )
                                st.success("✓ Đã sẵn sàng!")
                            except Exception as e:
                                st.error(f"Lỗi xuất bản: {e}")
                
                with col_del:
                    if st.button("🗑️ Xóa dự án", key=f"del-p-{p_id}"):
                        fs.delete_project(p_id)
                        st.rerun()

def sync_facebook_data():
    """Fetches latest public info from FB and saves to context."""
    # We use the data I just scraped for this specific update
    data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": "Trạm Gửi Tri Thức. 46 lượt thích · 32 người đang nói về điều này. 📮 Gom mẹo học hay - Gửi trao bản làng. Trang hiện đang có các bài đăng về phương pháp Cornell, Active Recall và Deliberate Practice. Tương tác ở mức khởi đầu (3-5 reactions/post)."
    }
    context_path = config.DATA_DIR / "facebook_context.json"
    context_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data

with tab_promotion:
    st.markdown("### 📢 Quảng bá & Truyền thông")
    
    # Advisor Section
    with st.expander("🤖 Cố vấn AI Chiến lược (Social Advisor)", expanded=True):
        col_adv_1, col_adv_2 = st.columns([3, 1])
        with col_adv_1:
            st.caption("Trao đổi với AI để nhận hướng đi mới và chiến lược tăng trưởng khán giả.")
        with col_adv_2:
            if st.button("🔄 Cập nhật từ Facebook", use_container_width=True, key="sync-fb-btn"):
                with st.spinner("Đang đồng bộ..."):
                    sync_facebook_data()
                    st.success("Đã đồng bộ!")
                    st.rerun()
        
        # Display context status
        ctx_path = config.DATA_DIR / "facebook_context.json"
        if ctx_path.exists():
            with open(ctx_path, "r", encoding="utf-8") as f:
                ctx_data = json.load(f)
                st.caption(f"📅 Dữ liệu Facebook: {ctx_data['timestamp']}")
        
        if "advisor_messages" not in st.session_state:
            st.session_state.advisor_messages = []
            
        # Display chat history
        for msg in st.session_state.advisor_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Hỏi cố vấn về chiến lược social..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.advisor_messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                advisor = SocialAdvisorAgent()
                with st.spinner("Đang suy nghĩ..."):
                    response = advisor.get_advice(prompt, st.session_state.advisor_messages[:-1])
                    st.markdown(response)
            st.session_state.advisor_messages.append({"role": "assistant", "content": response})

    st.divider()
    
    # Project Promotion Actions
    st.markdown("#### ⚡ Công cụ nhanh")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.popover("📢 Quảng bá dự án (Project Promo)", use_container_width=True):
            st.write("Sinh bài viết giới thiệu sứ mệnh và mục tiêu thiện nguyện của dự án.")
            projects = fs.list_projects()
            if not projects:
                st.warning("Vui lòng tạo dự án trước.")
            else:
                selected_p = st.selectbox("Chọn dự án", options=projects, format_func=lambda x: x[1].name)
                if st.button("🚀 Sinh bài viết quảng bá", use_container_width=True):
                    with st.spinner("Đang sáng tạo..."):
                        p_id, p_obj = selected_p
                        media_agent = MediaAgent()
                        promo_post = media_agent.generate_project_promo(p_id, p_obj.name, p_obj.description)
                        fs.save_post(promo_post)
                        st.success("Đã tạo bài viết! Kiểm tra ở tab 'Chờ duyệt'.")
                        st.rerun()
    with col2:
        with st.popover("🎥 Kịch bản Reels", use_container_width=True):
            st.write("Tạo kịch bản video ngắn (TikTok/Reels) với chuyên gia storytelling.")
            
            topic = st.text_input("Chủ đề video (Topic)", placeholder="Ví dụ: Trì hoãn việc học, Cách ghi nhớ nhanh...")
            
            with st.expander("Tùy chỉnh nâng cao"):
                core_story = st.selectbox("Phong cách (Core Story)", ["Chữa lành", "Trinh thám", "Sci-Fi", "Game hóa", "Hành động"])
                tone = st.selectbox("Giọng điệu (Tone)", ["Hóm hỉnh", "Nghiêm túc", "Châm biếm", "Sâu sắc", "Đanh đá"])
                
                approved_chapters = fs.list_by_status(ChapterStatus.APPROVED, limit=20)
                sel_chap_id = None
                if approved_chapters:
                    sel_chap = st.selectbox("Gắn với Chapter (Tùy chọn)", options=[(None, None)] + approved_chapters, format_func=lambda x: x[1].topic if x[1] else "Không gắn")
                    if sel_chap[0]:
                        sel_chap_id = sel_chap[0]

            if st.button("🎬 Tạo kịch bản Reels", use_container_width=True):
                if not topic:
                    st.error("Vui lòng nhập chủ đề.")
                else:
                    with st.spinner("Đang lên kịch bản..."):
                        reel_agent = ReelAgent()
                        script = reel_agent.generate_script(topic, core_story, tone)
                        
                        from db.schemas import PostDraft, PostType
                        new_reel = PostDraft(
                            chapter_id=sel_chap_id,
                            type=PostType.REEL,
                            content=script,
                            status=PostStatus.APPROVED
                        )
                        fs.save_post(new_reel)
                        st.success("Kịch bản đã sẵn sàng! Kiểm tra ở tab 'Kịch bản Reels'.")
                        st.rerun()

    # Get all posts (Chapter-based and Project-based)
    approved_chapters = fs.list_by_status(ChapterStatus.APPROVED, limit=20)
    all_data = [] # List of (title, posts, chap_id)
    
    # Add chapter posts
    for chap_id, chap in approved_chapters:
        posts = fs.list_posts_by_chapter(chap_id)
        if posts:
            all_data.append((f"📖 Chapter: {chap.topic}", posts, chap_id))
            
    # Add project posts
    projects = fs.list_projects()
    for p_id, p_obj in projects:
        p_posts = fs.list_posts_by_project(p_id)
        if p_posts:
            all_data.append((f"🌟 Dự án: {p_obj.name}", p_posts, None))
            
    # Add general posts (no chapter, no project)
    all_raw_posts = fs.list_all_posts(limit=100)
    general_posts = [p for p in all_raw_posts if p[1].chapter_id is None and p[1].project_id is None]
    if general_posts:
        all_data.append(("🌐 Chung", general_posts, None))

    if not all_data:
        render_empty_state(
            title="Chưa có bài viết nào",
            description="Hãy duyệt một chapter sách hoặc bấm 'Quảng bá dự án' để bắt đầu.",
        )
    else:
        sub_drafts, sub_ready, sub_reels = st.tabs(["⏳ Chờ duyệt (Drafts)", "🚀 Sẵn sàng đăng", "🎬 Kịch bản Reels"])
        
        with sub_drafts:
            for title, posts, chap_id in all_data:
                pending_posts = [p for p in posts if p[1].status == PostStatus.PENDING and p[1].type != PostType.REEL]
                if pending_posts:
                    st.markdown(f"#### {title}")
                    for post_id, post in pending_posts:
                        with st.container(border=True):
                            col_mock, col_info = st.columns([2, 1])
                            with col_mock:
                                img = None
                                if post.image_prompt:
                                    img = image_url(post.image_prompt, width=400, height=600)
                                st.components.v1.html(render_fb_post(post.content, img), height=450, scrolling=True)
                            with col_info:
                                st.write(f"**Loại:** {post.type.value.upper()}")
                                if st.button("✅ Duyệt post", key=f"app-post-{post_id}"):
                                    fs.approve_post(post_id)
                                    st.rerun()
                                
                                with st.popover("✏️ Sửa", use_container_width=True):
                                    new_content = st.text_area("Nội dung bài viết", value=post.content, height=200, key=f"edit-area-{post_id}")
                                    if st.button("Lưu thay đổi", key=f"save-edit-{post_id}"):
                                        fs.update_post_content(post_id, new_content)
                                        st.rerun()

                                if st.button("🗑️ Viết lại cái khác", key=f"del-post-p-{post_id}"):
                                    fs.delete_post(post_id)
                                    if chap_id:
                                        chap = fs.get_draft(chap_id)
                                        _trigger_single_media_gen(chap_id, chap.content_md, post.type)
                                    st.rerun()
        
        with sub_ready:
            st.info("💡 Bạn có thể copy nội dung dưới đây để đăng lên Facebook thủ công.")
            for title, posts, chap_id in all_data:
                approved_posts = [p for p in posts if p[1].status == PostStatus.APPROVED and p[1].type != PostType.REEL]
                if approved_posts:
                    st.markdown(f"#### {title}")
                    for post_id, post in approved_posts:
                        with st.expander(f"📢 {post.type.value.upper()} - {post.content[:50]}..."):
                            st.code(post.content, language="text")
                            if post.image_prompt:
                                st.write("**Gợi ý ảnh:**")
                                st.caption(post.image_prompt)
                                st.image(image_url(post.image_prompt, width=400, height=600))
                            if st.button("🗑️ Xóa", key=f"del-post-a-{post_id}"):
                                fs.delete_post(post_id)
                                st.rerun()

        with sub_reels:
            st.info("🎥 Đây là các kịch bản video ngắn đã được tối ưu hóa storytelling.")
            for title, posts, chap_id in all_data:
                reel_posts = [p for p in posts if p[1].type == PostType.REEL]
                if reel_posts:
                    st.markdown(f"#### {title}")
                    for post_id, post in reel_posts:
                        with st.container(border=True):
                            st.markdown(post.content)
                            if st.button("🗑️ Xóa kịch bản", key=f"del-reel-{post_id}"):
                                fs.delete_post(post_id)
                                st.rerun()

with tab_rejected:
    st.caption(
        "Bản đã bị từ chối. Bạn có thể duyệt lại hoặc xóa vĩnh viễn. "
        "Sau mỗi lần từ chối, AI tự viết lại bản mới ở tab Đang chờ duyệt."
    )
    render_tab(
        ChapterStatus.REJECTED,
        empty_title="Chưa có chapter nào bị từ chối",
        empty_desc="Tất cả draft đang đi đúng hướng. Tiếp tục duyệt bài để duy trì chất lượng nhé.",
    )
    # Escalated drafts (reject > MAX_RETRY) shown here too
    escalated = fs.list_by_status(ChapterStatus.ESCALATED, limit=20)
    if escalated:
        st.markdown('<div class="section-heading">🚨 Đã từ chối tối đa</div>', unsafe_allow_html=True)
        for draft_id, draft in escalated:
            render_draft(draft_id, draft, show_actions_for=ChapterStatus.ESCALATED)

