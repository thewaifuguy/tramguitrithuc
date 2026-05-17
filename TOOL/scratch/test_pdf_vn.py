import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from export.pdf_builder import build_chapter_pdf
from db.schemas import ChapterDraft

# Test Vietnamese content
test_topic = "Kiểm tra Tiếng Việt: Ăn quả nhớ kẻ trồng cây"
test_content = """
# Tiêu đề tiếng Việt
Nội dung có chứa các ký tự đặc biệt: **á à ả ã ạ, ă ắ ằ ẳ ẵ ặ, â ấ ầ ẩn ẫ ậ, đ, ê ế ề ể ễ ệ, ô ố hồ ổ ỗ ộ, ư ứ ừ ử ữ ự**.

## Danh sách kỹ năng
- Học tập chủ động
- Tư duy phản biện
- Sáng tạo và đổi mới

Cảm ơn bạn đã sử dụng hệ thống!
"""

try:
    print("Starting PDF generation test...")
    path = build_chapter_pdf("test_id", test_topic, test_content)
    print(f"PDF generated successfully at: {path}")
    print(f"File size: {Path(path).stat().st_size} bytes")
except Exception as e:
    print(f"Error during PDF generation: {e}")
    import traceback
    traceback.print_exc()
