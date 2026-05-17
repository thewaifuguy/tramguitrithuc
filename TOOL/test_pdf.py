import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent))

import logging
logging.basicConfig(level=logging.DEBUG)

from export.pdf_builder import build_chapter_pdf
from db.schemas import ChapterDraft

try:
    path = build_chapter_pdf("test_draft", "Test Topic", "Hello **world**!")
    print(f"PDF built successfully at: {path}")
except Exception as e:
    import traceback
    traceback.print_exc()
