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

import streamlit as st

# Make TOOL/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

import config
from agents.writer import WriterAgent
from db import storage as fs
from db.schemas import (
    REJECT_REASON_LABELS,
    ApprovalRecord,
    ChapterDraft,
    ChapterStatus,
    RejectEntry,
    RejectReason,
)
from integrations.pollinations import image_url


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_image_bytes(url: str) -> bytes | None:
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
render_sidebar()
render_how_it_works()
render_sample_card()


# === Generate new chapter (top action) ===

def _trigger_generate(topic: str, outline: str | None) -> bool:
    """Returns True nếu tạo thành công, False nếu fail."""
    try:
        with st.spinner(f"AI Writer đang viết chapter về '{topic}'..."):
            agent = WriterAgent()
            out = agent.generate_chapter(topic=topic, outline=outline)
            draft = ChapterDraft(
                topic=out.topic,
                content_md=out.content_md,
                image_prompts=out.image_prompts,
                input_tokens=out.input_tokens,
                output_tokens=out.output_tokens,
            )
            draft_id = fs.save_draft(draft)
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

st.markdown('<div class="section-heading">📋 Workspace</div>', unsafe_allow_html=True)


# === Tabs ===

tab_pending, tab_approved, tab_rejected = st.tabs(
    ["⏳ Đang chờ duyệt", "✅ Đã duyệt", "❌ Đã từ chối"]
)


def render_draft(draft_id: str, draft: ChapterDraft, show_actions_for: ChapterStatus | None = None) -> None:
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
                    _render_image_sidebar(draft.image_prompts)

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


def _render_image_sidebar(prompts: list[str]) -> None:
    """Fetch Pollinations images server-side with long timeout, cache 1h, then display."""
    st.caption("⏳ Lần đầu sinh ảnh mất 15-30s. Sau đó cache local sẽ hiện ngay.")
    for i, prompt in enumerate(prompts, 1):
        url = image_url(prompt, width=512, height=384)
        with st.spinner(f"Đang sinh ảnh #{i}..."):
            data = _fetch_image_bytes(url)
        if data:
            st.image(data, caption=f"Ảnh #{i}", use_container_width=True)
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
    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button("✅ Duyệt", key=f"approve-{draft_id}", type="primary", use_container_width=True):
            fs.approve_draft(draft_id)
            fs.log_approval(ApprovalRecord(draft_id=draft_id, action="approve"))
            st.session_state["_flash"] = ("success", "Đã duyệt chapter!")
            st.rerun()

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="❌ Từ chối / Viết lại")


def _render_approved_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_unapprove, col_reject, col_delete = st.columns(3)

    with col_unapprove:
        if st.button(
            "↩️ Trả về chờ duyệt",
            key=f"unapprove-{draft_id}",
            use_container_width=True,
            help="Đưa chapter này trở lại tab 'Đang chờ duyệt'",
        ):
            fs.set_status(draft_id, ChapterStatus.PENDING)
            st.session_state["_flash"] = ("success", "Đã trả về trạng thái chờ duyệt.")
            st.rerun()

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="❌ Từ chối / Viết lại")

    with col_delete:
        if st.button(
            "🗑️ Xóa",
            key=f"delete-approved-{draft_id}",
            use_container_width=True,
            help="Xóa vĩnh viễn",
        ):
            fs.delete_draft(draft_id)
            st.session_state["_flash"] = ("success", f"Đã xóa chapter ID {draft_id}.")
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


with tab_pending:
    render_tab(
        ChapterStatus.PENDING,
        empty_title="Chưa có draft nào đang chờ duyệt",
        empty_desc="Bấm vào một gợi ý phía trên hoặc nhập chủ đề riêng để AI bắt đầu viết chapter đầu tiên.",
        empty_cta="↑ Cuộn lên trên để tạo",
    )

with tab_approved:
    render_tab(
        ChapterStatus.APPROVED,
        empty_title="Chưa có chapter nào được duyệt",
        empty_desc="Khi bạn bấm '✅ Duyệt' cho một draft, nó sẽ xuất hiện ở đây và sẵn sàng để xuất bản.",
    )

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
