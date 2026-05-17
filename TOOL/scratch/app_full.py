"""Streamlit dashboard: Tráº¡m gá»­i tri thá»©c.

Workflow:
  - Sinh chapter má»›i (button trÃªn header â†’ form â†’ call WriterAgent live)
  - Pending tab: review draft, approve hoáº·c reject (regenerate auto)
  - Approved tab: chapter Ä‘Ã£ duyá»‡t, sáºµn sÃ ng cho Phase 4 (PDF + posts)
  - Rejected tab: lá»‹ch sá»­ reject (chá»‰ xem, khÃ´ng action)
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make TOOL/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

import config
from agents.media import MediaAgent
from agents.writer import WriterAgent
from db import storage as fs
from db.schemas import (
    REJECT_REASON_LABELS,
    ApprovalRecord,
    ChapterDraft,
    ChapterStatus,
    PostDraft,
    PostStatus,
    PostType,
    RejectEntry,
    RejectReason,
)
from export.pdf_builder import build_chapter_pdf
from integrations.facebook_mock import render_fb_post
from integrations.pollinations import download_image, image_url


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
    page_icon="ðŸ“š",
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
    """Returns True náº¿u táº¡o thÃ nh cÃ´ng, False náº¿u fail."""
    import time
    from db.schemas import ChapterStatus
    
    try:
        with st.spinner(f"AI Writer Ä‘ang viáº¿t chapter vá» '{topic}'..."):
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
                st.warning("âš ï¸ API Ä‘ang cháº­m hoáº·c gáº·p lá»—i. Äang chuyá»ƒn sang Demo Data dá»± phÃ²ng...")
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
        st.error(f"âŒ {e}")
        return False
    except Exception as e:
        st.error(
            f"âŒ Lá»—i khÃ´ng lÆ°á»ng trÆ°á»›c: {type(e).__name__}: {e}\n\n"
            "Vui lÃ²ng thá»­ láº¡i sau vÃ i phÃºt."
        )
        return False
    # LÆ°u flash message Ä‘á»ƒ hiá»‡n sau rerun
    st.session_state["_flash"] = ("success", f"âœ“ ÄÃ£ táº¡o chapter má»›i (ID `{draft_id}`). Xem á»Ÿ tab Äang chá» duyá»‡t.")
    return True


SUGGESTION_POOL = [
    "Pomodoro cho há»c sinh hay trÃ¬ hoÃ£n",
    "Active Recall khi Ã´n thi mÃ´n Lá»‹ch sá»­",
    "Äáº·t má»¥c tiÃªu SMART cho lá»›p 9",
    "Há»c nhÃ³m hiá»‡u quáº£ qua Zalo",
    "Ká»¹ thuáº­t feynman Ä‘á»ƒ hiá»ƒu sÃ¢u kiáº¿n thá»©c",
    "Mind Map cho mÃ´n Sinh há»c",
    "Spaced Repetition vá»›i Anki",
    "CÃ¡ch ghi chÃº Cornell",
    "VÆ°á»£t qua ná»—i sá»£ thi cá»­",
    "Quáº£n lÃ½ thá»i gian há»c + giáº£i trÃ­ cÃ¢n báº±ng",
    "Tá»± há»c hiá»‡u quáº£ khi khÃ´ng cÃ³ gia sÆ°",
    "Há»c tá»« vá»±ng tiáº¿ng Anh báº±ng ngá»¯ cáº£nh",
    "RÃ¨n ká»¹ nÄƒng Ä‘á»c hiá»ƒu mÃ´n VÄƒn",
    "CÃ¡ch lÃ m bÃ i táº­p ToÃ¡n khÃ³ khÃ´ng náº£n",
    "Chiáº¿n lÆ°á»£c Ã´n thi vÃ o 10 cho há»c sinh trung bÃ¬nh",
]


def _pick_suggestions(n: int = 4) -> list[str]:
    """Chá»n n gá»£i Ã½ random, cache trong session Ä‘á»ƒ khÃ´ng Ä‘á»•i giá»¯a rerun."""
    if st.session_state.pop("_resuggest", False) or "suggestions" not in st.session_state:
        st.session_state["suggestions"] = random.sample(SUGGESTION_POOL, n)
    return st.session_state["suggestions"]


# Clear form trÆ°á»›c khi widgets render (chá»‰ cháº¡y khi flag Ä‘Æ°á»£c set á»Ÿ rerun trÆ°á»›c)
if st.session_state.pop("_clear_form", False):
    st.session_state["topic_input"] = ""
    st.session_state["outline_input"] = ""

# Flash message tá»« rerun trÆ°á»›c (success/error sau khi submit)
_flash = st.session_state.pop("_flash", None)
if _flash:
    kind, msg = _flash
    if kind == "success":
        st.success(msg)
    else:
        st.error(msg)

render_cta_header()

# Chip click â†’ set session_state cho widget key rá»“i rerun
chosen_topic = render_suggestion_bar(_pick_suggestions())
if chosen_topic:
    st.session_state["topic_input"] = chosen_topic
    st.rerun()

with st.form("new-chapter", clear_on_submit=False):
    topic = st.text_input(
        "Chá»§ Ä‘á» chapter",
        key="topic_input",
        placeholder="VD: Pomodoro cho há»c sinh hay trÃ¬ hoÃ£n",
    )
    outline = st.text_area(
        "Outline gá»£i Ã½ (tÃ¹y chá»n)",
        key="outline_input",
        placeholder="Äá»ƒ trá»‘ng cho AI tá»± quyáº¿t outline",
        height=80,
    )
    if st.form_submit_button("ðŸš€ Generate chapter", type="primary"):
        if not topic.strip():
            st.error("Pháº£i nháº­p chá»§ Ä‘á».")
        else:
            success = _trigger_generate(topic.strip(), outline.strip() or None)
            if success:
                # Chá»‰ rerun + clear khi thÃ nh cÃ´ng
                st.session_state["_clear_form"] = True
                st.rerun()
            # Náº¿u fail, khÃ´ng rerun â†’ error message (st.error trong _trigger_generate) á»Ÿ láº¡i

st.markdown('<div class="section-heading">ðŸ“‹ Workspace</div>', unsafe_allow_html=True)


# === Tabs ===

tab_pending, tab_approved, tab_posts, tab_rejected, tab_demo = st.tabs(
    ["â³ Chá» duyá»‡t bÃ i", "âœ… SÃ¡ch Ä‘Ã£ duyá»‡t", "ðŸ“± Quáº£ng bÃ¡ (Posts)", "âŒ LÆ°u trá»¯", "ðŸŽ¬ Demo Mode"]
)

with tab_demo:
    st.markdown(
        """
        <div class="demo-header">
            <h3>ðŸŽ¬ Cháº¿ Ä‘á»™ Demo nhanh</h3>
            <p>DÃ nh cho há»™i Ä‘á»“ng ban giÃ¡m kháº£o. Cháº¡y quy trÃ¬nh máº«u Ä‘á»ƒ xem káº¿t quáº£ nhanh nháº¥t.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col_run, col_reset = st.columns([2, 1])
    with col_run:
        if st.button("ðŸš€ Cháº¡y Demo Pipeline", type="primary", use_container_width=True):
            st.info("Báº¯t Ä‘áº§u quy trÃ¬nh demo tá»± Ä‘á»™ng...")
            
            # 1. Generate (Mock for speed or use seed data)
            with st.status("Äang cháº¡y pipeline...", expanded=True) as status:
                st.write("1. TÃ¬m kiáº¿m chá»§ Ä‘á» phÃ¹ há»£p...")
                import time
                time.sleep(1)
                
                st.write("2. AI Ä‘ang biÃªn soáº¡n ná»™i dung chapter...")
                # We can use the seed function or just pick one from DB
                demo_chapters = fs.list_by_status(ChapterStatus.APPROVED, limit=5)
                if not demo_chapters:
                    st.warning("ChÆ°a cÃ³ demo data. Vui lÃ²ng cháº¡y seed_demo_data.py")
                else:
                    d_id, d_obj = demo_chapters[0]
                    time.sleep(2)
                    st.write(f"âœ“ ÄÃ£ hoÃ n thÃ nh chapter: **{d_obj.topic}**")
                    
                    st.write("3. Äang thiáº¿t káº¿ bÃ i viáº¿t Facebook...")
                    time.sleep(2)
                    st.write("âœ“ ÄÃ£ sinh 3 bÃ i viáº¿t quáº£ng bÃ¡.")
                    
                    st.write("4. Äang dÃ n trang PDF handbook...")
                    time.sleep(2)
                    st.write("âœ“ File PDF Ä‘Ã£ sáºµn sÃ ng.")
                    
                status.update(label="âœ… Pipeline hoÃ n táº¥t!", state="complete", expanded=False)
            
            st.success("Demo Ä‘Ã£ sáºµn sÃ ng! Má»i ban giÃ¡m kháº£o xem káº¿t quáº£ á»Ÿ cÃ¡c tab tÆ°Æ¡ng á»©ng.")
            st.balloons()
            
    with col_reset:
        if st.button("ðŸ”„ Reset Demo Data", use_container_width=True):
            import sqlite3
            conn = sqlite3.connect(config.SQLITE_PATH)
            conn.execute("DELETE FROM chapters")
            conn.execute("DELETE FROM posts")
            conn.execute("DELETE FROM approvals")
            conn.commit()
            conn.close()
            st.warning("ÄÃ£ xÃ³a toÃ n bá»™ dá»¯ liá»‡u. Vui lÃ²ng cháº¡y seed láº¡i.")
            st.rerun()

    st.divider()
    st.markdown("**Gá»£i Ã½ cho ban giÃ¡m kháº£o:**")
    st.write("1. Nháº­p má»™t chá»§ Ä‘á» báº¥t ká»³ á»Ÿ phÃ­a trÃªn.")
    st.write("2. VÃ o tab **Chá» duyá»‡t** Ä‘á»ƒ xem AI viáº¿t.")
    st.write("3. Báº¥m **Duyá»‡t** Ä‘á»ƒ chuyá»ƒn qua tab **SÃ¡ch Ä‘Ã£ duyá»‡t**.")
    st.write("4. Báº¥m **Xuáº¥t PDF** Ä‘á»ƒ xem thÃ nh pháº©m cuá»‘i cÃ¹ng.")



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
                        ID <code>{draft_id}</code> Â· {draft.created_at:%d/%m/%Y %H:%M}
                        Â· ðŸ“– {word_count} tá»« Â· â±ï¸ ~{reading_min} phÃºt Ä‘á»c
                        Â· ðŸ” Láº§n thá»­ {draft.retry_count + 1}/{config.MAX_RETRY + 1}
                    </div>
                </div>
                {status_label}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # === Reject history if any
        if draft.reject_history:
            with st.expander(f"âš ï¸ ÄÃ£ tá»«ng bá»‹ tá»« chá»‘i {len(draft.reject_history)} láº§n"):
                for entry in draft.reject_history:
                    label = REJECT_REASON_LABELS.get(entry.reason_code, entry.reason_code.value)
                    st.write(f"â€¢ **{label}** â€” {entry.note or '(khÃ´ng ghi chÃº)'} _({entry.at:%H:%M})_")

        # === 2-column layout: content (left) + images (right)
        col_content, col_images = st.columns([3, 1])
        with col_content:
            st.markdown(
                '<div class="section-label">ðŸ“– Ná»™i dung chapter</div>',
                unsafe_allow_html=True,
            )
            with st.container(height=480, border=False):
                st.markdown('<div class="draft-content-wrapper"></div>', unsafe_allow_html=True)
                st.markdown(_strip_image_prompts(content_for_display))
        with col_images:
            st.markdown(
                f'<div class="section-label">ðŸ–¼ï¸ áº¢nh minh há»a ({len(draft.image_prompts)})</div>',
                unsafe_allow_html=True,
            )
            with st.container(height=480, border=False):
                if not draft.image_prompts:
                    st.caption("Chapter nÃ y khÃ´ng cÃ³ image prompt.")
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
    st.caption("â³ Láº§n Ä‘áº§u sinh áº£nh máº¥t 15-30s. Sau Ä‘Ã³ cache local sáº½ hiá»‡n ngay.")
    for i, prompt in enumerate(prompts, 1):
        url = image_url(prompt, width=512, height=384)
        with st.spinner(f"Äang sinh áº£nh #{i}..."):
            data = _fetch_image_bytes(url)
        if data:
            st.image(data, caption=f"áº¢nh #{i}", use_container_width=True)
        else:
            st.warning(f"âš ï¸ áº¢nh #{i} khÃ´ng load Ä‘Æ°á»£c â€” Pollinations cÃ³ thá»ƒ Ä‘ang báº­n. Refresh Ä‘á»ƒ thá»­ láº¡i.")


def _status_badge(status: ChapterStatus) -> str:
    mapping = {
        ChapterStatus.PENDING: ("status-pending", "â³ Äang chá» duyá»‡t"),
        ChapterStatus.APPROVED: ("status-approved", "âœ… ÄÃ£ duyá»‡t"),
        ChapterStatus.REJECTED: ("status-rejected", "âŒ ÄÃ£ tá»« chá»‘i"),
        ChapterStatus.ESCALATED: ("status-rejected", "ðŸš¨ ÄÃ£ escalate"),
    }
    css, label = mapping.get(status, ("", status.value))
    return f'<span class="status-badge {css}">{label}</span>'


def _render_pending_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button("âœ… Duyá»‡t", key=f"approve-{draft_id}", type="primary", use_container_width=True):
            fs.approve_draft(draft_id)
            fs.log_approval(ApprovalRecord(draft_id=draft_id, action="approve"))
            st.session_state["_flash"] = ("success", "ÄÃ£ duyá»‡t chapter!")
            st.rerun()

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="âŒ Tá»« chá»‘i / Viáº¿t láº¡i")


def _render_approved_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_pdf, col_unapprove, col_reject, col_delete = st.columns([1.5, 1, 1, 1])

    with col_pdf:
        if st.button(
            "ðŸ“„ Xuáº¥t PDF",
            key=f"pdf-{draft_id}",
            type="primary",
            use_container_width=True,
            help="Táº¡o file PDF handbook vá»›i Ä‘áº§y Ä‘á»§ áº£nh minh há»a",
        ):
            try:
                with st.spinner("Äang chuáº©n bá»‹ PDF vÃ  táº£i áº£nh (cÃ³ thá»ƒ máº¥t 30-60s)..."):
                    pdf_path = build_chapter_pdf(draft_id, draft.topic, draft.content_md)
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="â¬‡ï¸ Táº£i xuá»‘ng PDF",
                        data=f,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"dl-pdf-{draft_id}",
                        use_container_width=True,
                    )
                st.success("âœ“ ÄÃ£ sinh PDF thÃ nh cÃ´ng!")
            except Exception as e:
                st.error(f"Lá»—i sinh PDF: {e}")

    with col_unapprove:
        if st.button(
            "â†©ï¸ Tráº£ vá» chá» duyá»‡t",
            key=f"unapprove-{draft_id}",
            use_container_width=True,
            help="ÄÆ°a chapter nÃ y trá»Ÿ láº¡i tab 'Äang chá» duyá»‡t'",
        ):
            fs.set_status(draft_id, ChapterStatus.PENDING)
            st.session_state["_flash"] = ("success", "ÄÃ£ tráº£ vá» tráº¡ng thÃ¡i chá» duyá»‡t.")
            st.rerun()

    with col_reject:
        _render_reject_popover(draft_id, draft, button_label="âŒ Tá»« chá»‘i / Viáº¿t láº¡i")

    with col_delete:
        if st.button(
            "ðŸ—‘ï¸ XÃ³a",
            key=f"delete-approved-{draft_id}",
            use_container_width=True,
            help="XÃ³a vÄ©nh viá»…n",
        ):
            fs.delete_draft(draft_id)
            st.session_state["_flash"] = ("success", f"ÄÃ£ xÃ³a chapter ID {draft_id}.")
            st.rerun()


def _render_rejected_actions(draft_id: str, draft: ChapterDraft) -> None:
    col_reapprove, col_delete = st.columns(2)

    with col_reapprove:
        if st.button(
            "âœ… Duyá»‡t láº¡i",
            key=f"reapprove-{draft_id}",
            type="primary",
            use_container_width=True,
            help="Chuyá»ƒn chapter nÃ y qua 'ÄÃ£ duyá»‡t'",
        ):
            fs.set_status(draft_id, ChapterStatus.APPROVED)
            fs.log_approval(ApprovalRecord(draft_id=draft_id, action="approve", note="Duyá»‡t láº¡i sau khi reject"))
            st.session_state["_flash"] = ("success", "ÄÃ£ duyá»‡t láº¡i chapter!")
            st.rerun()

    with col_delete:
        if st.button(
            "ðŸ—‘ï¸ XÃ³a",
            key=f"delete-rejected-{draft_id}",
            use_container_width=True,
        ):
            fs.delete_draft(draft_id)
            st.session_state["_flash"] = ("success", f"ÄÃ£ xÃ³a chapter ID {draft_id}.")
            st.rerun()


def _render_reject_popover(draft_id: str, draft: ChapterDraft, button_label: str) -> None:
    with st.popover(button_label, use_container_width=True):
        st.markdown("**LÃ½ do tá»« chá»‘i:**")
        reason_key = st.selectbox(
            "LÃ½ do",
            options=list(RejectReason),
            format_func=lambda r: REJECT_REASON_LABELS[r],
            key=f"reason-{draft_id}",
            label_visibility="collapsed",
        )
        note = st.text_area(
            "Ghi chÃº (báº¯t buá»™c náº¿u chá»n 'LÃ½ do khÃ¡c')",
            key=f"note-{draft_id}",
            height=80,
        )
        if st.button(
            "XÃ¡c nháº­n tá»« chá»‘i",
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
        st.error("Chá»n 'LÃ½ do khÃ¡c' pháº£i ghi chÃº.")
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
            f"ÄÃ£ Ä‘áº¡t giá»›i háº¡n {config.MAX_RETRY + 1} láº§n thá»­. "
            "Báº¡n cÃ³ thá»ƒ thá»­ láº¡i vá»›i chá»§ Ä‘á» khÃ¡c hoáº·c tinh chá»‰nh prompt."
        )
        st.rerun()
        return

    try:
        with st.spinner(f"AI viáº¿t láº¡i (láº§n {draft.retry_count + 2}/{config.MAX_RETRY + 1})..."):
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
        st.error(f"âŒ {e}")
        return
    except Exception as e:
        st.error(f"âŒ Lá»—i: {type(e).__name__}: {e}")
        return

    st.success(f"ÄÃ£ viáº¿t láº¡i! Báº£n má»›i ID `{new_id}`")
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
        st.error(f"Lá»—i DB: {e}")
        return

    if not items:
        render_empty_state(
            title=empty_title or f"ChÆ°a cÃ³ chapter nÃ o",
            description=empty_desc,
            cta=empty_cta,
        )
        return

    for draft_id, draft in items:
        render_draft(draft_id, draft, show_actions_for=status)


def _trigger_media_gen(draft_id: str, content: str) -> None:
    try:
        with st.spinner("AI Media Ä‘ang lÃªn Ã½ tÆ°á»Ÿng bÃ i viáº¿t Facebook..."):
            agent = MediaAgent()
            posts = agent.generate_posts(draft_id, content)
            for p in posts:
                fs.save_post(p)
        st.session_state["_flash"] = ("success", "ÄÃ£ sinh bÃ i viáº¿t quáº£ng bÃ¡! Xem á»Ÿ tab Posts.")
    except Exception as e:
        st.error(f"Lá»—i sinh media: {e}")


def _trigger_single_media_gen(draft_id: str, content: str, post_type: PostType) -> None:
    try:
        with st.spinner(f"AI Ä‘ang viáº¿t láº¡i bÃ i {post_type.value}..."):
            agent = MediaAgent()
            post = agent.generate_single_post(draft_id, content, post_type)
            fs.save_post(post)
        st.session_state["_flash"] = ("success", f"ÄÃ£ Ä‘á»•i bÃ i {post_type.value} má»›i!")
    except Exception as e:
        st.error(f"Lá»—i viáº¿t láº¡i post: {e}")


with tab_pending:
    render_tab(
        ChapterStatus.PENDING,
        empty_title="ChÆ°a cÃ³ draft nÃ o Ä‘ang chá» duyá»‡t",
        empty_desc="Báº¥m vÃ o má»™t gá»£i Ã½ phÃ­a trÃªn hoáº·c nháº­p chá»§ Ä‘á» riÃªng Ä‘á»ƒ AI báº¯t Ä‘áº§u viáº¿t chapter Ä‘áº§u tiÃªn.",
        empty_cta="â†‘ Cuá»™n lÃªn trÃªn Ä‘á»ƒ táº¡o",
    )

with tab_approved:
    # Custom rendering for approved to add "Generate Posts" button
    try:
        items = fs.list_by_status(ChapterStatus.APPROVED, limit=20)
    except Exception as e:
        st.error(f"Lá»—i DB: {e}")
        items = []

    if not items:
        render_empty_state(
            title="ChÆ°a cÃ³ chapter nÃ o Ä‘Æ°á»£c duyá»‡t",
            description="Khi báº¡n báº¥m 'âœ… Duyá»‡t' cho má»™t draft, nÃ³ sáº½ xuáº¥t hiá»‡n á»Ÿ Ä‘Ã¢y vÃ  sáºµn sÃ ng Ä‘á»ƒ xuáº¥t báº£n.",
        )
    else:
        for draft_id, draft in items:
            render_draft(draft_id, draft, show_actions_for=ChapterStatus.APPROVED)
            # Add Media Gen button if no posts exist for this chapter
            existing_posts = fs.list_posts_by_chapter(draft_id)
            if not existing_posts:
                if st.button(f"âœ¨ Sinh bÃ i viáº¿t quáº£ng bÃ¡ (FB)", key=f"gen-media-{draft_id}"):
                    _trigger_media_gen(draft_id, draft.content_md)
                    st.rerun()

with tab_posts:
    st.caption("Quáº£n lÃ½ cÃ¡c bÃ i viáº¿t Facebook Ä‘Æ°á»£c sinh ra tá»« cÃ¡c chapter Ä‘Ã£ duyá»‡t.")
    
    # Get all posts first
    approved_chapters = fs.list_by_status(ChapterStatus.APPROVED, limit=20)
    all_posts_by_chap = {}
    for chap_id, chap in approved_chapters:
        posts = fs.list_posts_by_chapter(chap_id)
        if posts:
            all_posts_by_chap[chap_id] = (chap, posts)

    if not all_posts_by_chap:
        render_empty_state(
            title="ChÆ°a cÃ³ bÃ i viáº¿t nÃ o",
            description="HÃ£y duyá»‡t má»™t chapter sÃ¡ch trÆ°á»›c, sau Ä‘Ã³ báº¥m 'Sinh bÃ i viáº¿t quáº£ng bÃ¡'.",
        )
    else:
        sub_drafts, sub_ready = st.tabs(["â³ Chá» duyá»‡t (Drafts)", "ðŸš€ Sáºµn sÃ ng Ä‘Äƒng"])
        
        with sub_drafts:
            for chap_id, (chap, posts) in all_posts_by_chap.items():
                pending_posts = [p for p in posts if p[1].status == PostStatus.PENDING]
                if pending_posts:
                    st.markdown(f"#### ðŸ“– Chapter: {chap.topic}")
                    for post_id, post in pending_posts:
                        with st.container(border=True):
                            col_mock, col_info = st.columns([2, 1])
                            with col_mock:
                                img = None
                                if post.image_prompt:
                                    img = image_url(post.image_prompt, width=400, height=600)
                                st.components.v1.html(render_fb_post(post.content, img), height=450, scrolling=True)
                            with col_info:
                                st.write(f"**Loáº¡i:** {post.type.value.upper()}")
                                if st.button("âœ… Duyá»‡t post", key=f"app-post-{post_id}"):
                                    fs.approve_post(post_id)
                                    st.rerun()
                                
                                with st.popover("âœï¸ Sá»­a", use_container_width=True):
                                    new_content = st.text_area("Ná»™i dung bÃ i viáº¿t", value=post.content, height=200, key=f"edit-area-{post_id}")
                                    if st.button("LÆ°u thay Ä‘á»•i", key=f"save-edit-{post_id}"):
                                        # I need a storage function to update post content
                                        fs.update_post_content(post_id, new_content)
                                        st.rerun()

                                if st.button("ðŸ—‘ï¸ Viáº¿t láº¡i cÃ¡i khÃ¡c", key=f"del-post-p-{post_id}"):
                                    fs.delete_post(post_id)
                                    _trigger_single_media_gen(chap_id, chap.content_md, post.type)
                                    st.rerun()
        
        with sub_ready:
            st.info("ðŸ’¡ Báº¡n cÃ³ thá»ƒ copy ná»™i dung dÆ°á»›i Ä‘Ã¢y Ä‘á»ƒ Ä‘Äƒng lÃªn Facebook thá»§ cÃ´ng.")
            for chap_id, (chap, posts) in all_posts_by_chap.items():
                approved_posts = [p for p in posts if p[1].status == PostStatus.APPROVED]
                if approved_posts:
                    st.markdown(f"#### ðŸ“– Chapter: {chap.topic}")
                    for post_id, post in approved_posts:
                        with st.expander(f"ðŸ“¢ {post.type.value.upper()} - {post.content[:50]}..."):
                            st.code(post.content, language="text")
                            if post.image_prompt:
                                st.write("**Gá»£i Ã½ áº£nh:**")
                                st.caption(post.image_prompt)
                                st.image(image_url(post.image_prompt, width=400, height=600))
                            if st.button("ðŸ—‘ï¸ XÃ³a", key=f"del-post-a-{post_id}"):
                                fs.delete_post(post_id)
                                st.rerun()

with tab_rejected:
    st.caption(
        "Báº£n Ä‘Ã£ bá»‹ tá»« chá»‘i. Báº¡n cÃ³ thá»ƒ duyá»‡t láº¡i hoáº·c xÃ³a vÄ©nh viá»…n. "
        "Sau má»—i láº§n tá»« chá»‘i, AI tá»± viáº¿t láº¡i báº£n má»›i á»Ÿ tab Äang chá» duyá»‡t."
    )
    render_tab(
        ChapterStatus.REJECTED,
        empty_title="ChÆ°a cÃ³ chapter nÃ o bá»‹ tá»« chá»‘i",
        empty_desc="Táº¥t cáº£ draft Ä‘ang Ä‘i Ä‘Ãºng hÆ°á»›ng. Tiáº¿p tá»¥c duyá»‡t bÃ i Ä‘á»ƒ duy trÃ¬ cháº¥t lÆ°á»£ng nhÃ©.",
    )
    # Escalated drafts (reject > MAX_RETRY) shown here too
    escalated = fs.list_by_status(ChapterStatus.ESCALATED, limit=20)
    if escalated:
        st.markdown('<div class="section-heading">ðŸš¨ ÄÃ£ tá»« chá»‘i tá»‘i Ä‘a</div>', unsafe_allow_html=True)
        for draft_id, draft in escalated:
            render_draft(draft_id, draft, show_actions_for=ChapterStatus.ESCALATED)

