# Implementation Plan - Day 3: Media Agent & FB Mock

This plan covers the implementation of the Media Agent for generating Facebook posts and the corresponding UI in the dashboard.

## Phase 1: Database & Schemas
1.  **Modify `db/schemas.py`**:
    - Add `PostType` enum (CAROUSEL, SHORT, REEL).
    - Add `PostDraft` Pydantic model.
2.  **Modify `db/storage.py`**:
    - Update `_SCHEMA` to include the `posts` table.
    - Add `save_post(post: PostDraft) -> str`.
    - Add `list_posts_by_chapter(chapter_id: str) -> list[tuple[str, PostDraft]]`.
    - Add `approve_post(post_id: str)`.
    - Add `delete_post(post_id: str)`.

## Phase 2: Media Agent
1.  **Create `prompts/media_system.md`**:
    - System prompt for Gemini to write engaging educational FB posts in Vietnamese.
2.  **Create `agents/media.py`**:
    - Implement `MediaAgent(BaseAgent)`.
    - Method `generate_posts(chapter_content: str) -> list[PostDraft]`.

## Phase 3: FB Mock Integration
1.  **Create `integrations/facebook_mock.py`**:
    - Function `render_fb_post(content: str, image_url: str | None = None)` that returns a styled HTML string.

## Phase 4: Dashboard Integration
1.  **Modify `dashboard/app.py`**:
    - Add `tab_posts` to the `st.tabs` call.
    - Implement logic to list approved chapters and their corresponding posts.
    - Add a button "Generate Posts" for approved chapters that don't have posts yet.
    - Implement the "Posts" tab UI with 2 sub-tabs:
        - **Drafts**: List of pending posts with FB Mock preview and "Approve" button.
        - **Ready to Post**: List of approved posts with easy "Copy" interface for manual posting.

## Verification Checkpoints
1.  [ ] Schema updated and `posts` table created in SQLite.
2.  [ ] `MediaAgent` successfully generates 3 posts from a chapter.
3.  [ ] FB Mock renders correctly in Streamlit.
4.  [ ] "Posts" tab displays drafts and allows approval.
