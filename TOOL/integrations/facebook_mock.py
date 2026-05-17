"""Facebook Post Mock: render HTML that looks like a FB post for Streamlit."""

from __future__ import annotations

import base64
from pathlib import Path

import config

def render_fb_post(content: str, image_url: str | None = None) -> str:
    """Returns a string of HTML/CSS for a Facebook post preview."""
    
    # Try to load logo for avatar
    avatar_src = "https://via.placeholder.com/40"
    logo_path = config.ASSETS_DIR / "logo.png"
    if logo_path.exists():
        ext = logo_path.suffix.lstrip('.')
        data = base64.b64encode(logo_path.read_bytes()).decode()
        avatar_src = f"data:image/{ext};base64,{data}"
        # Fixed below
    
    # Random engagement counts
    import random
    likes = random.randint(10, 150)
    comments = random.randint(2, 25)
    shares = random.randint(1, 10)
    
    html = f"""
    <style>
    .fb-card {{
        background: white;
        border: 1px solid #dddfe2;
        border-radius: 8px;
        padding: 12px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        max-width: 500px;
        margin: 10px auto;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .fb-header {{
        display: flex;
        align-items: center;
        margin-bottom: 12px;
    }}
    .fb-avatar {{
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #2C5F5C;
        margin-right: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
    }}
    .fb-name-block {{
        line-height: 1.2;
    }}
    .fb-name {{
        font-weight: 600;
        color: #050505;
        font-size: 15px;
        cursor: pointer;
    }}
    .fb-name:hover {{ text-decoration: underline; }}
    .fb-time {{
        color: #65676b;
        font-size: 13px;
    }}
    .fb-content {{
        font-size: 14px;
        color: #050505;
        line-height: 1.5;
        white-space: pre-wrap;
        margin-bottom: 10px;
    }}
    .fb-image {{
        width: calc(100% + 24px);
        margin: 10px -12px;
        border-top: 1px solid #dddfe2;
        border-bottom: 1px solid #dddfe2;
    }}
    .fb-engagement {{
        padding: 8px 0;
        border-bottom: 1px solid #ebedf0;
        font-size: 13px;
        color: #65676b;
        display: flex;
        justify-content: space-between;
    }}
    .fb-footer {{
        margin-top: 4px;
        padding-top: 4px;
        display: flex;
        justify-content: space-around;
        color: #65676b;
        font-size: 14px;
        font-weight: 600;
    }}
    .fb-action {{
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        flex: 1;
        text-align: center;
    }}
    .fb-action:hover {{ background: #f2f2f2; }}
    </style>
    <div class="fb-card">
        <div class="fb-header">
            <div class="fb-avatar">T</div>
            <div class="fb-name-block">
                <div class="fb-name">{config.BRAND_NAME}</div>
                <div class="fb-time">Vừa xong · 🌐</div>
            </div>
        </div>
        <div class="fb-content">{content}</div>
        {f'<img class="fb-image" src="{image_url}" />' if image_url else ''}
        <div class="fb-engagement">
            <span>👍 {likes}</span>
            <span>{comments} bình luận · {shares} chia sẻ</span>
        </div>
        <div class="fb-footer">
            <div class="fb-action">👍 Thích</div>
            <div class="fb-action">💬 Bình luận</div>
            <div class="fb-action">↪️ Chia sẻ</div>
        </div>
    </div>
    """
    return html
