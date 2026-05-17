"""Seed demo data: pre-generate a few chapters and posts for the demo."""

import sys
from pathlib import Path
from datetime import datetime

# Make TOOL/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from db import storage as fs
from db.schemas import ChapterDraft, ChapterStatus, PostDraft, PostType, PostStatus, Project

DEMO_DATA = [
    {
        "topic": "Pomodoro: Kỹ thuật 'Quả cà chua' trị trì hoãn",
        "content_md": """# Pomodoro: Kỹ thuật 'Quả cà chua' trị trì hoãn

Bạn có bao giờ thấy mình ngồi vào bàn học nhưng lại cầm điện thoại lên suốt 2 tiếng không? Đó chính là sự trì hoãn - "kẻ thù" số 1 của học sinh.

## 🍅 Phương pháp Pomodoro là gì?
Pomodoro (tiếng Ý là quả cà chua) là kỹ thuật quản lý thời gian cực kỳ hiệu quả. Ý tưởng rất đơn giản: Tập trung tuyệt đối trong 25 phút, sau đó nghỉ ngơi 5 phút.

<!-- IMAGE_PROMPT: Pure black line art illustration on white background, minimal clean style, a floating tomato-shaped timer with glowing aura, no shading, no colors, high contrast, pure black ink -->

## 🚀 Cách thực hiện 5 bước
1. **Chọn việc cần làm:** Ví dụ: Giải 3 bài tập Toán.
2. **Hẹn giờ 25 phút:** Trong lúc này, KHÔNG làm gì khác.
3. **Làm cho đến khi chuông reo.**
4. **Nghỉ ngắn 5 phút:** Đứng dậy, vươn vai.
5. **Sau 4 lần, nghỉ dài 15-30 phút.**

<!-- IMAGE_PROMPT: Pure black line art illustration on white background, minimal clean style, a stack of books with a digital timer on top showing 25:00, no shading, no colors, high contrast, pure black ink -->

## 💡 Tại sao nó hiệu quả?
Khi biết mình chỉ phải tập trung trong 25 phút, não bộ sẽ ít cảm thấy "ngợp" hơn. Nó giống như một cuộc chạy nước rút ngắn thay vì một cuộc marathon mệt mỏi.

## 📝 Thử thách hôm nay
Hãy thử áp dụng 1 Pomodoro cho môn học bạn ngại nhất. Chỉ 25 phút thôi, bạn làm được mà!

## Tóm tắt cho phụ huynh

> **Dành cho bố mẹ:** Phương pháp Pomodoro giúp các con rèn luyện khả năng tập trung sâu (Deep Work) và giảm căng thẳng khi đối mặt với khối lượng bài tập lớn. Bố mẹ có thể hỗ trợ bằng cách nhắc con nghỉ ngơi đúng 5 phút sau mỗi phiên học, tránh để con sa đà vào thiết bị điện tử trong lúc giải lao.
""",
        "image_prompts": [
            "Pure black line art illustration on white background, minimal clean style, a floating tomato-shaped timer with glowing aura, no shading, no colors, high contrast, pure black ink",
            "Pure black line art illustration on white background, minimal clean style, a stack of books with a digital timer on top showing 25:00, no shading, no colors, high contrast, pure black ink"
        ]
    }
]

def seed():
    print("Seeding demo data...")
    
    # Ensure a demo project exists
    p_id = "demo-project"
    try:
        if not fs.get_project(p_id):
            fs.save_project(Project(name="Demo Project", description="Dữ liệu mẫu cho buổi thuyết trình"))
            # Note: save_project returns a new ID, but for seed we might want a fixed one or handle it
            # Let's just list and pick the first or create one.
    except:
        fs.save_project(Project(name="Demo Project", description="Dữ liệu mẫu cho buổi thuyết trình"))
    
    # Get the project ID
    projects = fs.list_projects()
    demo_p_id = projects[0][0] if projects else None

    for item in DEMO_DATA:
        # Save as approved chapter
        draft = ChapterDraft(
            project_id=demo_p_id,
            topic=item["topic"],
            content_md=item["content_md"],
            image_prompts=item["image_prompts"],
            status=ChapterStatus.APPROVED,
            approved_at=datetime.now()
        )
        draft_id = fs.save_draft(draft)
        print(f"Created chapter ID: {draft_id}")
        
        # Add some posts
        posts = [
            PostDraft(
                chapter_id=draft_id,
                project_id=demo_p_id,
                type=PostType.SHORT,
                content=f"Bạn có hay trì hoãn khi học không? Thử ngay Pomodoro - kỹ thuật 'quả cà chua' giúp tập trung 100%! #HocTap #Pomodoro #TramGuiTriThuc",
                image_prompt="A professional digital collage poster featuring a central, surreal red tomato timer on a student desk. Risograph texture, film grain, neon teal and coral palette.",
                status=PostStatus.APPROVED
            ),
            PostDraft(
                chapter_id=draft_id,
                project_id=demo_p_id,
                type=PostType.INFORMATIVE,
                content="Làm sao để tập trung 100% trong 25 phút?\n\n1. Chọn 1 việc duy nhất\n2. Hẹn giờ 25 phút\n3. Làm hết sức mình\n4. Nghỉ 5 phút\n\nLặp lại và bạn sẽ thấy điều kỳ diệu!",
                image_prompt="A professional digital collage poster featuring a surreal clock melting over a stack of school books. Risograph texture, tactile noise, vibrant purple and yellow palette.",
                status=PostStatus.PENDING
            )
        ]
        for p in posts:
            fs.save_post(p)
        print(f"Created 2 posts for chapter {draft_id}")

    print("Seeding complete!")

if __name__ == "__main__":
    seed()
