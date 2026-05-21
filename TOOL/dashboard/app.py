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
_TOOL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_TOOL_ROOT))

st.set_page_config(
    page_title="Trạm gửi tri thức",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

import requests

from gemini_secrets import inject_gemini_key_to_env

inject_gemini_key_to_env()


def _ensure_api_key() -> None:
    """Secrets + optional manual key from sidebar."""
    import os

    inject_gemini_key_to_env()
    manual = st.session_state.get("manual_gemini_key")
    if manual:
        os.environ["GEMINI_API_KEY"] = manual


_ensure_api_key()

import config
from agents.media import MediaAgent
from agents.writer import WriterAgent
from agents.critic import CriticAgent
import json
import datetime
from agents.advisor import SocialAdvisorAgent
from agents.reel import ReelAgent

# Reload DB layer only (do not reload config — breaks Cloud deploy)
import importlib
import db.schemas
import db.storage
importlib.reload(db.schemas)
importlib.reload(db.storage)
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
from dashboard.sample_pdf import (
    SAMPLE_HANDBOOK_FILENAME,
    SAMPLE_HANDBOOK_TITLE,
    get_sample_handbook_bytes,
    sample_handbook_download_name,
    sample_handbook_path,
)
from dashboard.showcase import ensure_demo_seeded, run_fast_showcase
from scripts.seed_demo_data import DEMO_DATA

# Initialize session state for page routing
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "landing"

# PAGE ROUTING
if st.session_state["current_page"] == "landing":
    import textwrap
    
    st.markdown(
        textwrap.dedent(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;800;900&display=swap');

            :root {
                --bg-dark: #050508;
                --text-white: #ffffff;
                --text-muted: #8e8e9f;
                --primary-grad: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            }

            .stApp {
                background-color: var(--bg-dark) !important;
                font-family: 'Montserrat', sans-serif !important;
            }

            /* Hide Streamlit components */
            header[data-testid="stHeader"], footer {
                background: transparent !important;
                display: none !important;
            }
            
            .main-container {
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 95vh;
                padding: 40px 20px;
            }

            .landing-logo {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 50px;
            }

            @media (max-width: 991px) {
                .landing-logo {
                    justify-content: center;
                    margin-bottom: 30px;
                }
            }

            .logo-icon {
                font-size: 28px;
                background: var(--primary-grad);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
            }

            .logo-text {
                font-family: 'Montserrat', sans-serif;
                font-weight: 900;
                font-size: 20px;
                color: var(--text-white);
                letter-spacing: 1px;
                text-transform: uppercase;
            }

            .welcome-txt {
                font-family: 'Montserrat', sans-serif;
                font-size: 88px;
                font-weight: 900;
                line-height: 1.0;
                color: var(--text-white);
                margin: 0;
                letter-spacing: -3px;
            }

            .project-title {
                font-family: 'Montserrat', sans-serif;
                font-size: 48px;
                font-weight: 800;
                line-height: 1.1;
                background: linear-gradient(135deg, #60a5fa 0%, #c084fc 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 10px 0 25px 0;
                letter-spacing: -1px;
            }

            .slogan {
                font-size: 13px;
                font-weight: 800;
                color: #a7f3d0;
                text-transform: uppercase;
                letter-spacing: 3px;
                margin-bottom: 15px;
            }

            .hero-desc {
                font-size: 15px;
                line-height: 1.8;
                color: var(--text-muted);
                max-width: 540px;
                margin-bottom: 40px;
            }

            /* Streamlit Button overrides for landing page only */
            div.stButton > button {
                border-radius: 9999px !important;
                font-family: 'Montserrat', sans-serif !important;
                font-weight: 700 !important;
                font-size: 15px !important;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                height: 52px !important;
                border: none !important;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important;
                color: #ffffff !important;
                box-shadow: 0 4px 20px rgba(59, 130, 246, 0.4) !important;
            }

            div.stButton > button:hover {
                transform: translateY(-3px) scale(1.02) !important;
                box-shadow: 0 6px 25px rgba(59, 130, 246, 0.6) !important;
            }

            .graphic-side {
                position: relative;
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                height: 480px;
            }

            .floating-card {
                position: absolute;
                right: 20px;
                bottom: 20px;
                background: rgba(13, 13, 20, 0.7);
                backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 24px;
                max-width: 280px;
                text-align: left;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                z-index: 5;
            }

            .card-logo {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 12px;
            }

            .card-logo-icon {
                font-size: 20px;
                color: #c084fc;
            }

            .card-logo-txt {
                font-family: 'Montserrat', sans-serif;
                font-weight: 800;
                font-size: 13px;
                color: var(--text-white);
                letter-spacing: 0.5px;
            }

            .card-title {
                font-family: 'Montserrat', sans-serif;
                font-size: 20px;
                font-weight: 700;
                color: var(--text-white);
                margin: 0 0 10px 0;
            }

            .card-desc {
                font-size: 12px;
                color: var(--text-muted);
                line-height: 1.6;
                margin: 0;
            }

            /* Flame flickering animation */
            @keyframes flicker {
                0%, 100% {
                    transform: scale(1) translate(0, 0);
                    opacity: 0.95;
                }
                20% {
                    transform: scale(0.95, 1.05) translate(-1px, 1px);
                    opacity: 0.85;
                }
                40% {
                    transform: scale(1.05, 0.95) translate(1px, -1px);
                    opacity: 0.90;
                }
                60% {
                    transform: scale(0.97, 1.03) translate(-1px, -1px);
                    opacity: 0.88;
                }
                80% {
                    transform: scale(1.03, 0.97) translate(1px, 1px);
                    opacity: 0.93;
                }
            }

            .flame-core {
                transform-origin: 300px 285px;
                animation: flicker 0.15s infinite alternate ease-in-out;
            }

            /* Concentric light waves animation */
            @keyframes lightWave {
                0% {
                    transform: scale(0.4);
                    opacity: 0.8;
                }
                100% {
                    transform: scale(1.3);
                    opacity: 0;
                }
            }

            .glow-wave {
                transform-origin: 300px 265px;
                animation: lightWave 4s infinite linear;
            }

            .glow-wave-1 { animation-delay: 0s; }
            .glow-wave-2 { animation-delay: 1.33s; }
            .glow-wave-3 { animation-delay: 2.66s; }

            /* Magic floating sparkles animation */
            @keyframes floatSparkle {
                0% {
                    transform: translateY(0) scale(0);
                    opacity: 0;
                }
                50% {
                    opacity: 0.8;
                }
                100% {
                    transform: translateY(-120px) scale(1.2);
                    opacity: 0;
                }
            }

            .sparkle {
                animation: floatSparkle 6s infinite ease-out;
            }

            .sparkle-1 { animation-delay: 0.5s; transform-origin: 280px 250px; }
            .sparkle-2 { animation-delay: 2.5s; transform-origin: 320px 220px; }
            .sparkle-3 { animation-delay: 4.5s; transform-origin: 290px 280px; }
            </style>
            """
        ),
        unsafe_allow_html=True
    )

    # 2-column layout in Streamlit
    col_left, col_right = st.columns([1.2, 1])
    
    with col_left:
        st.markdown(
            textwrap.dedent(
                """
                <div class="landing-logo">
                    <span class="logo-icon">📖</span>
                    <span class="logo-text">Trạm gửi tri thức</span>
                </div>
                
                <h1 class="welcome-txt">Welcome.</h1>
                <h2 class="project-title">Trạm gửi tri thức.</h2>
                <div class="slogan">Đánh thức tư duy · Kết nối bản làng</div>
                
                <p class="hero-desc">
                    Nền tảng tự động hóa biên soạn học liệu bằng Trí tuệ nhân tạo (AI) 
                    của tập thể học sinh lớp 8A5. Chúng mình giúp rút ngắn khoảng cách 
                    giáo dục cho trẻ em vùng cao biên giới Chiềng Chăn bằng công nghệ thông minh.
                </p>
                """
            ),
            unsafe_allow_html=True
        )
        
        # Native Streamlit buttons styled perfectly
        st.write("") # Add a little spacing
        if st.button("🚀 Bắt đầu Sử dụng App", key="landing_btn_app", use_container_width=True):
            st.session_state["current_page"] = "app"
            st.rerun()
                
    with col_right:
        st.markdown(
            """<div class="graphic-side"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="100%" height="100%" fill="none" style="filter: drop-shadow(0 0 25px rgba(245, 158, 11, 0.1));"><defs><linearGradient id="warmGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#f59e0b" stop-opacity="0.8"/><stop offset="50%" stop-color="#ef4444" stop-opacity="0.8"/><stop offset="100%" stop-color="#ec4899" stop-opacity="0.8"/></linearGradient><linearGradient id="flameGrad" x1="0%" y1="100%" x2="0%" y2="0%"><stop offset="0%" stop-color="#ef4444" stop-opacity="1"/><stop offset="40%" stop-color="#f59e0b" stop-opacity="1"/><stop offset="85%" stop-color="#fef08a" stop-opacity="1"/><stop offset="100%" stop-color="#ffffff" stop-opacity="0.9"/></linearGradient><radialGradient id="lanternGlow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#f59e0b" stop-opacity="0.25"/><stop offset="50%" stop-color="#ef4444" stop-opacity="0.08"/><stop offset="100%" stop-color="#050508" stop-opacity="0"/></radialGradient><filter id="flameBlur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3" result="blur"/><feComposite in="SourceGraphic" in2="blur" operator="over"/></filter></defs><circle cx="300" cy="265" r="220" fill="url(#lanternGlow)"/><circle cx="300" cy="265" r="70" class="glow-wave glow-wave-1"/><circle cx="300" cy="265" r="130" class="glow-wave glow-wave-2"/><circle cx="300" cy="265" r="190" class="glow-wave glow-wave-3"/><path d="M 120,200 C 180,180 240,220 300,210 C 360,200 420,160 480,180" stroke="rgba(245, 158, 11, 0.12)" stroke-width="1.5" /><path d="M 100,260 C 170,230 230,280 300,270 C 370,260 430,210 500,240" stroke="rgba(245, 158, 11, 0.16)" stroke-width="1.5" stroke-dasharray="3,3" /><path d="M 80,320 C 160,290 220,340 300,330 C 380,320 440,270 520,300" stroke="rgba(245, 158, 11, 0.08)" stroke-width="1.5" /><path d="M 280,210 L 282,215 L 287,217 L 282,219 L 280,224 L 278,219 L 273,217 L 278,215 Z" class="sparkle sparkle-1"/><path d="M 325,180 L 327,183 L 332,185 L 327,187 L 325,192 L 323,187 L 318,185 L 323,183 Z" class="sparkle sparkle-2"/><path d="M 295,150 L 297,153 L 302,155 L 297,157 L 295,162 L 293,157 L 288,155 L 293,153 Z" class="sparkle sparkle-3"/><path d="M 230,220 C 230,80 370,80 370,220" stroke="#4b5563" stroke-width="3" fill="none" stroke-linecap="round"/><path d="M 255,210 L 345,210 L 330,175 L 270,175 Z" fill="#2d3748" stroke="#1a202c" stroke-width="2"/><rect x="275" y="160" width="50" height="15" rx="3" fill="#1a202c"/><rect x="285" y="145" width="30" height="15" rx="2" fill="#4a5568"/><circle cx="300" cy="152" r="3" fill="#d97706"/><path d="M 255,210 C 240,250 240,320 255,360 L 345,360 C 360,320 360,250 345,210 Z" fill="rgba(255, 255, 255, 0.04)" stroke="rgba(255, 255, 255, 0.25)" stroke-width="1.5"/><path d="M 270,210 C 258,260 258,310 270,360" fill="none" stroke="#4b5563" stroke-width="2"/><path d="M 330,210 C 342,260 342,310 330,360" fill="none" stroke="#4b5563" stroke-width="2"/><path class="flame-core" d="M 300,240 C 285,275 282,305 300,305 C 318,305 315,275 300,240 Z" fill="url(#flameGrad)" filter="url(#flameBlur)"/><path d="M 240,360 C 240,360 220,370 220,395 L 380,395 C 380,370 360,360 360,360 Z" fill="#2d3748" stroke="#1a202c" stroke-width="2"/><rect x="205" y="395" width="190" height="25" rx="5" fill="#1a202c"/><circle cx="370" cy="382" r="7" fill="#d97706"/><rect x="368" y="370" width="4" height="12" fill="#b45309"/></svg><div class="floating-card"><div class="card-logo"><span class="card-logo-icon">💠</span><span class="card-logo-txt">Sứ mệnh GCED</span></div><h3 class="card-title">Hành trình 8A5.</h3><p class="card-desc">Không chỉ là công nghệ AI, đây là khát vọng mang cơ hội giáo dục bình đẳng đến học sinh vùng cao khó khăn.</p></div></div>""",
            unsafe_allow_html=True
        )
    st.stop()



# If APP mode, show a small action bar at the very top to go back to Home
col_back_home, _ = st.columns([2, 5])
with col_back_home:
    if st.button("↩️ Quay lại Trang chủ", use_container_width=True, key="back-home-top-btn"):
        st.session_state["current_page"] = "landing"
        st.rerun()

apply_theme()
render_hero()
render_sample_card()


# === Generate new chapter (top action) ===

def _trigger_generate(topic: str, outline: str | None) -> bool:
    """Returns True nếu tạo thành công, False nếu fail."""
    import os
    import time
    from db.schemas import ChapterStatus

    _ensure_api_key()

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
                st.warning("⚠️ API lỗi — dùng Demo Data. Tip: tab Demo → **Showcase ~15 giây**.")
                time.sleep(0.5)
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


def run_demo_pipeline(topic: str) -> None:
    """Full demo with optional AI (slower). PDF step prefers pre-built sample file."""
    status_area = st.empty()
    progress_bar = st.progress(0)

    status_area.info(f"🚀 **Bước 1/4:** AI Writer đang biên soạn chapter: *{topic}*...")
    progress_bar.progress(10)
    _ensure_api_key()

    try:
        from agents.writer import WriterAgent

        writer = WriterAgent()
        draft_obj = writer.generate_chapter(topic)
        draft_id = fs.save_draft(draft_obj)
        progress_bar.progress(40)
        st.success(f"✅ Đã soạn xong chapter. ID: `{draft_id}`")
    except Exception as e:
        st.warning(f"⚠️ API lỗi — dùng Demo Data. Tip: **Showcase ~15 giây**.")
        item = DEMO_DATA[0]
        draft_obj = ChapterDraft(
            topic=item["topic"],
            content_md=item["content_md"],
            image_prompts=item["image_prompts"],
            status=ChapterStatus.APPROVED,
            approved_at=datetime.now(),
        )
        draft_id = fs.save_draft(draft_obj)
        topic = draft_obj.topic
        st.info(f"💡 Demo data. Handbook: **{SAMPLE_HANDBOOK_TITLE}**.")
        progress_bar.progress(40)

    status_area.info("🔍 **Bước 2/4:** AI Critic đang kiểm duyệt...")
    import time

    time.sleep(0.5)
    fs.update_status(draft_id, ChapterStatus.APPROVED)
    progress_bar.progress(60)
    st.success("✅ Đã phê duyệt (Quality Passed).")

    status_area.info("📱 **Bước 3/4:** AI Media...")
    try:
        from agents.media import MediaAgent

        posts = MediaAgent().generate_posts(draft_id, draft_obj.content_md)
    except Exception:
        posts = [
            PostDraft(
                chapter_id=draft_id,
                type=PostType.SHORT,
                content="Mẹo tập trung Pomodoro...",
                status=PostStatus.APPROVED,
            )
        ]

    for p in posts:
        p.status = PostStatus.APPROVED
        fs.save_post(p)
    progress_bar.progress(80)
    st.success(f"✅ {len(posts)} bài quảng bá.")

    status_area.info("📄 **Bước 4/4:** Handbook PDF...")
    pdf_bytes = get_sample_handbook_bytes()
    if pdf_bytes:
        pdf_data = pdf_bytes
        download_name = sample_handbook_download_name()
        st.success(f"✅ {SAMPLE_HANDBOOK_TITLE}")
    else:
        from export.pdf_builder import build_chapter_pdf

        pdf_path = build_chapter_pdf(draft_id, topic, draft_obj.content_md)
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        download_name = f"{topic}.pdf"
        st.success("✅ PDF sinh từ nội dung mới.")

    progress_bar.progress(100)
    status_area.success("🎊 **QUY TRÌNH HOÀN TẤT!**")
    st.balloons()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📖 Handbook PDF")
        st.download_button(
            label="⬇️ Tải xuống Handbook",
            data=pdf_data,
            file_name=download_name,
            mime="application/pdf",
            use_container_width=True,
            key="download-demo-pipeline-handbook",
        )
    with c2:
        st.markdown("#### 📱 Facebook Posts")
        st.info("Tab **Quảng bá (Social)**.")


# === Tabs ===

tab_intro, tab_landing, tab_pending, tab_approved, tab_projects, tab_promotion, tab_rejected, tab_demo = st.tabs(
    ["ℹ️ Giới thiệu", "🌐 Landing Page 3D", "⏳ Chờ duyệt bài", "✅ Sách đã duyệt", "📚 Dự án (Projects)", "📢 Quảng bá (Social)", "❌ Lịch sử từ chối", "🎬 Demo Mode"]
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

with tab_landing:
    st.markdown("### 🌐 Trải nghiệm Trạm Gửi Tri Thức 3D")
    st.caption("Trải nghiệm không gian 3D tương tác kể câu chuyện dự án (Cuộn dọc trong khung dưới để xem mô hình 3D biến đổi).")
    
    # Read and render the HTML component
    landing_path = Path(__file__).parent / "assets" / "landing.html"
    if landing_path.exists():
        with open(landing_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        import streamlit.components.v1 as components
        components.html(html_content, height=800, scrolling=False)
    else:
        st.error("Không tìm thấy tệp landing.html trong dashboard/assets!")

with tab_demo:
    ensure_demo_seeded(fs)

    st.markdown(
        """
        <div class="demo-header">
            <h3>🎬 Showcase (trình diễn nhanh)</h3>
            <p><b>Khuyên dùng khi thi:</b> nút vàng <b>Showcase ~15 giây</b> — không cần API, có PDF + posts ngay.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_info, col_reset = st.columns([2, 1])
    with col_reset:
        if st.button("🗑️ Xóa toàn bộ dữ liệu", use_container_width=True):
            fs.clear_all()
            st.session_state.pop("demo_seeded", None)
            st.warning("Đã xóa toàn bộ DB. Hãy rerun app.")
            st.rerun()

    st.divider()
    demo_topic = st.text_input(
        "Chủ đề trình diễn",
        value="Kỹ thuật Pomodoro cho học sinh hay trì hoãn",
        help="Showcase: chỉ đổi tiêu đề hiển thị; nội dung dùng bản demo đã chuẩn bị.",
    )

    col_fast, col_full, col_quick = st.columns(3)
    with col_fast:
        if st.button(
            "⚡ Showcase ~15 giây",
            type="primary",
            use_container_width=True,
            help="Không gọi Gemini — nhanh nhất cho buổi thi",
        ):
            if not demo_topic.strip():
                st.error("Nhập chủ đề trước.")
            else:
                run_fast_showcase(
                    fs,
                    demo_topic,
                    demo_data=DEMO_DATA,
                    get_pdf_bytes=get_sample_handbook_bytes,
                    pdf_download_name=sample_handbook_download_name(),
                    handbook_title=SAMPLE_HANDBOOK_TITLE,
                )
    with col_full:
        if st.button(
            "🏁 Demo đầy đủ (có AI)",
            use_container_width=True,
            help="Gọi Gemini — có thể 30s–2 phút hoặc lỗi API",
        ):
            if not demo_topic:
                st.error("Vui lòng nhập chủ đề.")
            else:
                run_demo_pipeline(demo_topic)
    with col_quick:
        pdf_bytes = get_sample_handbook_bytes()
        if pdf_bytes:
            st.download_button(
                label="⚡ Handbook mẫu: Đánh thức tư duy",
                data=pdf_bytes,
                file_name=sample_handbook_download_name(),
                mime="application/pdf",
                use_container_width=True,
                help=f"Tải ngay PDF mẫu — {SAMPLE_HANDBOOK_TITLE}",
                key="download-quick-handbook",
            )
        else:
            st.button(
                "⚡ Handbook mẫu (chưa có PDF trên server)",
                disabled=True,
                use_container_width=True,
            )

    st.divider()
    st.markdown("**Kịch bản nhanh (~2 phút):**")
    st.markdown(
        "1. **Showcase ~15 giây** → progress 4 bước → tải PDF  \n"
        "2. Tab **Quảng bá** → preview Facebook  \n"
        "3. (Tuỳ chọn) Tab **Chờ duyệt** / **Sách đã duyệt**"
    )


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

    _ensure_api_key()
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

