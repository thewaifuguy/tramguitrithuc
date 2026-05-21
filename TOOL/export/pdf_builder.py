"""PDF Builder: convert Markdown to branded PDF using WeasyPrint (Modern) or xhtml2pdf (Fallback)."""

from __future__ import annotations

import re
import base64
import logging
from pathlib import Path

from typing import List, Tuple, TYPE_CHECKING, Optional

import markdown
import config
from integrations.pollinations import download_image, image_url

if TYPE_CHECKING:
    from db.schemas import ChapterDraft, Project

# Configure logging to see import issues
logger = logging.getLogger(__name__)

# --- PDF Engine Setup ---
HAS_WEASYPRINT = False
HAS_PISA = False
WEASY_IMPORT_ERROR = ""
pisa = None  # type: ignore

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except Exception as e:
    WEASY_IMPORT_ERROR = str(e)
    logger.warning(f"WeasyPrint not available: {e}. Using xhtml2pdf on Streamlit/local.")

try:
    from xhtml2pdf import pisa as _pisa
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pisa = _pisa
    HAS_PISA = True
    font_dir = Path(__file__).parent.parent / "fonts"
    try:
        pdfmetrics.registerFont(TTFont("BeVietnamPro", str(font_dir / "BeVietnamPro-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("BeVietnamPro-Bold", str(font_dir / "BeVietnamPro-Bold.ttf")))
    except Exception as font_err:
        logger.warning(f"Could not register custom TTF fonts: {font_err}")
except ImportError:
    logger.error("xhtml2pdf is not installed — PDF export will fail.")

def build_chapter_pdf(draft_id: str, topic: str, content_md: str) -> Path:
    """Processes chapter content and returns path to generated PDF."""
    output_dir = config.OUTPUT_DIR / "pdf" / draft_id
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    pdf_path = output_dir / f"{topic.replace(' ', '_')}.pdf"
    
    processed_md = content_md
    prompts = re.findall(r"<!--\s*IMAGE_PROMPT:\s*(.*?)\s*-->", content_md)
    
    for i, prompt in enumerate(prompts):
        img_filename = f"image_{i}.png"
        img_path = images_dir / img_filename
        if not img_path.exists():
            url = image_url(prompt, width=1024, height=768)
            download_image(url, img_path)
        tag = f"<!-- IMAGE_PROMPT: {prompt} -->"
        img_url_str = img_path.absolute().as_uri()
        processed_md = processed_md.replace(tag, f"![image_{i}]({img_url_str})")
    
    html_content = markdown.markdown(processed_md, extensions=['extra', 'smarty', 'nl2br'])
    chapter_content = f'''
    <div class="chapter-container">
        <div class="chapter-content">
            <h1 class="chapter-title">{topic}</h1>
            {html_content}
        </div>
    </div>
    '''
    full_html = _wrap_in_template(topic, chapter_content, is_project=False)
    return _generate_pdf(full_html, pdf_path)

def build_project_pdf(project_id: str, project_name: str, chapters: List[Tuple[str, "ChapterDraft"]]) -> Path:
    """Merges multiple chapters into one handbook PDF."""
    from db.storage import get_project
    project_obj = get_project(project_id)
    
    output_dir = config.OUTPUT_DIR / "projects" / project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{project_name.replace(' ', '_')}.pdf"
    
    front_cover = '<div class="front-cover"></div>'
    foreword = f'''
    <div class="foreword">
        <h2>Lời nói đầu</h2>
        <p>Chào mừng bạn đến với cuốn cẩm nang <b>{project_name}</b>. Cẩm nang này được biên soạn với mục đích chia sẻ kiến thức, kinh nghiệm và những phương pháp hữu ích nhất để phát triển kỹ năng.</p>
        <p>Hành trình tiếp thu tri thức chưa bao giờ là dễ dàng, nhưng với công cụ phù hợp và sự bền bỉ, chúng tôi tin rằng bạn sẽ đạt được mục tiêu của mình.</p>
    </div>
    '''
    
    toc_html = "<div class='toc'><h2>Mục lục</h2><ul class='toc-list'>"
    full_body = ""
    for i, (c_id, c_obj) in enumerate(chapters):
        chapter_num = i + 1
        chapter_html_id = f"chapter_{chapter_num}"
        chapter_end_id = f"chapter_{chapter_num}_end"
        toc_html += f"<li><a href='#{chapter_html_id}' data-end='#{chapter_end_id}'><span class='title'>Chương {chapter_num}: {c_obj.topic}</span></a></li>"
        
        processed_md = _inject_auto_summaries(c_obj.content_md)
        images_dir = output_dir / "images" / c_id
        images_dir.mkdir(parents=True, exist_ok=True)
        
        prompts = re.findall(r"<!--\s*IMAGE_PROMPT:\s*(.*?)\s*-->", processed_md)
        for j, prompt in enumerate(prompts):
            img_filename = f"image_{j}.png"
            img_path = images_dir / img_filename
            if not img_path.exists():
                url = image_url(prompt, width=1024, height=768)
                download_image(url, img_path)
            tag = f"<!-- IMAGE_PROMPT: {prompt} -->"
            img_url_str = img_path.absolute().as_uri()
            processed_md = processed_md.replace(tag, f"![image_{j}]({img_url_str})")
        
        html_chapter = markdown.markdown(processed_md, extensions=['extra', 'smarty', 'nl2br'])
        
        chapter_img_url = ""
        if c_obj.cover_path and Path(c_obj.cover_path).exists():
            chapter_img_url = Path(c_obj.cover_path).absolute().as_uri()
        elif project_obj and project_obj.chapter_image_path and Path(project_obj.chapter_image_path).exists():
            chapter_img_url = Path(project_obj.chapter_image_path).absolute().as_uri()

        # Build the chapter title page (Full Page Image)
        # Using a direct <img> tag with object-fit: cover for maximum reliability in PDF rendering
        if chapter_img_url:
            chapter_title_page = f'''
            <div class="chapter-title-page-placeholder" id="{chapter_html_id}">
                <img src="{chapter_img_url}" style="width: 100%; height: 100%; object-fit: cover; display: block; margin: 0; padding: 0;">
            </div>
            '''
        else:
            chapter_title_page = f'''
            <div class="chapter-title-page-placeholder" id="{chapter_html_id}" style="background-color: #f9f9f9;">
                 &nbsp;
            </div>
            '''
        
        full_body += f'''
        <div class="chapter-container">
            {chapter_title_page}
            <div class="chapter-content">
                <h1 class="chapter-title-display">{c_obj.topic}</h1>
                {html_chapter}
            </div>
            <div id="{chapter_end_id}"></div>
        </div>
        '''
        
    toc_html += "</ul></div>"
    back_cover = '<div class="back-cover"></div>'
    
    content_with_covers = f"{front_cover}{foreword}{toc_html}{full_body}{back_cover}"
    full_html = _wrap_in_template(project_name, content_with_covers, is_project=True, project_assets=project_obj)
    return _generate_pdf(full_html, pdf_path)

def _inject_auto_summaries(markdown_text: str) -> str:
    return markdown_text

def _generate_pdf(full_html: str, pdf_path: Path) -> Path:
    logger.info(f"Generating PDF at: {pdf_path}")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if HAS_WEASYPRINT:
        try:
            HTML(string=full_html).write_pdf(str(pdf_path))
            return pdf_path
        except Exception as e:
            logger.warning(f"WeasyPrint PDF failed: {e}. Trying xhtml2pdf.")

    if not HAS_PISA or pisa is None:
        raise RuntimeError(
            "Không có engine PDF (cần xhtml2pdf). Trên Streamlit Cloud dùng handbook mẫu có sẵn."
        )

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(full_html, dest=f, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed with error code {result.err}")
    return pdf_path

def _wrap_in_template(topic: str, html_content: str, is_project: bool = False, project_assets: Optional[Project] = None) -> str:
    logo_data = ""
    if config.LOGO_PATH.exists():
        encoded = base64.b64encode(config.LOGO_PATH.read_bytes()).decode()
        logo_data = f"data:image/png;base64,{encoded}"
    
    font_dir = Path(__file__).parent.parent / "fonts"
    font_header = font_dir / "Montserrat-Bold.ttf"
    font_header_url = f"file:///{font_header.absolute().as_posix()}"

    front_cover_url = ""
    chapter_image_url = ""
    back_cover_url = ""
    if project_assets:
        if project_assets.front_cover_path and Path(project_assets.front_cover_path).exists():
            front_cover_url = Path(project_assets.front_cover_path).absolute().as_uri()
        if project_assets.chapter_image_path and Path(project_assets.chapter_image_path).exists():
            chapter_image_url = Path(project_assets.chapter_image_path).absolute().as_uri()
        if project_assets.back_cover_path and Path(project_assets.back_cover_path).exists():
            back_cover_url = Path(project_assets.back_cover_path).absolute().as_uri()

    # Pre-calculate styles to avoid complex f-string interpolation
    front_bg = f"url('{front_cover_url}')" if front_cover_url else "#2C5F5C"
    back_bg = f"url('{back_cover_url}')" if back_cover_url else "#2C5F5C"

    weasy_css = f"""
        @page {{
            size: A5;
            margin: 15mm 10mm;
            @top-left {{ content: string(chapter_title); font-family: 'Montserrat', sans-serif; font-size: 7pt; color: #888; }}
            @top-right {{ content: "{config.BRAND_NAME}"; font-family: 'Montserrat', sans-serif; font-size: 7pt; color: #888; }}
        }}
        .chapter-content-wrapper {{ position: relative; min-height: 100%; }}
        .chapter-content {{
            text-align: justify; word-wrap: break-word; overflow-wrap: break-word;
            min-height: 180mm; font-family: 'Times New Roman', serif;
        }}
        img {{ max-width: 100%; height: auto; display: block; margin: 10mm auto; border-radius: 5px; }}
        
        @page front-cover {{ margin: 0; background: {front_bg} no-repeat center; background-size: cover; }}
        @page back-cover {{ margin: 0; background: {back_bg} no-repeat center; background-size: cover; }}
        @page toc {{ margin: 20mm 20mm; }}
        @page foreword {{ margin: 20mm 20mm; }}
        @page chapter-title {{ margin: 0; }}
        
        .front-cover {{ page: front-cover; height: 100vh; }}
        .back-cover {{ page: back-cover; height: 100vh; }}
        .foreword {{ page: foreword; page-break-after: always; }}
        .toc {{ page: toc; page-break-before: right; page-break-after: right; }}
        .toc-list {{ list-style: none; padding: 0; }}
        .toc-list li {{ margin-bottom: 10px; font-family: 'Montserrat', sans-serif; font-weight: bold; }}
        
        .chapter-content {{ page: chapter_content; }}
        .chapter-title-page-placeholder {{ 
            page: chapter-title; 
            page-break-after: always; 
            height: 210mm; 
            width: 148mm;
            margin: 0;
            padding: 0;
            overflow: hidden;
            position: relative;
        }}
        h1, h2, h3 {{ color: #2C5F5C; font-family: 'Montserrat', sans-serif; font-weight: bold; }}
        h1 {{ font-size: 22pt; string-set: chapter_title content(); }}
        p, li {{ font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; text-align: justify; }}
    """

    header_html = f'''
        <div class="logo-container" style="text-align:center; margin-bottom:20px;">
            {f'<img src="{logo_data}" style="width:60px;">' if logo_data else ""}
        </div>
    ''' if not is_project else ''

    footer_html = f'''
        <div class="footer" style="text-align:center; font-size:8pt; color:#888; margin-top:20px;">
            © 2026 {config.BRAND_NAME}
        </div>
    ''' if not is_project else ''

    html_template = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <style>
            @font-face {{ font-family: 'Montserrat'; src: url('{font_header_url}'); font-weight: bold; font-style: normal; }}
            body {{ font-family: 'Times New Roman', serif; font-size: 11pt; line-height: 1.6; color: #333; margin: 0; padding: 0; word-wrap: break-word; overflow-wrap: break-word; width: 100%; }}
            /* WEASY_CSS_PLACEHOLDER */
        </style>
    </head>
    <body>
        {header_html}
        <div class="content">
            <div class="chapter-content-wrapper">
                {html_content}
            </div>
        </div>
        {footer_html}
    </body>
    </html>
    """
    return html_template.replace("/* WEASY_CSS_PLACEHOLDER */", weasy_css)