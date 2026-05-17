import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import storage as fs
from db.schemas import ChapterDraft, ChapterStatus
from agents.media import MediaAgent

def test_media_flow():
    # 1. Create an approved chapter if none exists
    approved = fs.list_by_status(ChapterStatus.APPROVED, limit=1)
    if not approved:
        print("Creating mock approved chapter...")
        draft = ChapterDraft(
            topic="Test Topic",
            content_md="# Test Content\nThis is a test chapter about learning methods.",
            status=ChapterStatus.APPROVED
        )
        chap_id = fs.save_draft(draft)
    else:
        chap_id, draft = approved[0]
        print(f"Using existing approved chapter ID: {chap_id}")

    # 2. Generate posts
    print("Generating posts...")
    agent = MediaAgent()
    posts = agent.generate_posts(chap_id, draft.content_md)
    
    print(f"Generated {len(posts)} posts:")
    for p in posts:
        post_id = fs.save_post(p)
        print(f" - [{p.type.value}] ID: {post_id}")

    # 3. List posts
    l = fs.list_posts_by_chapter(chap_id)
    print(f"Total posts for chapter {chap_id} in DB: {len(l)}")
    assert len(l) > 0
    print("Test PASSED!")

if __name__ == "__main__":
    test_media_flow()
