"""SQLite storage layer. Same interface as the old firestore_client so the rest
of the app doesn't care which backend is in use.

Schema is created lazily on first use (no migrations needed for demo scope).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import config
from db.schemas import (
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


_SCHEMA = """
CREATE TABLE IF NOT EXISTS chapters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    content_md      TEXT NOT NULL,
    image_prompts   TEXT NOT NULL,        -- JSON list[str]
    status          TEXT NOT NULL,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    parent_id       INTEGER,
    reject_history  TEXT NOT NULL DEFAULT '[]',  -- JSON list[RejectEntry]
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    project_id      INTEGER,              -- Link to projects
    cover_path      TEXT,                 -- Chapter-specific cover
    created_at      TEXT NOT NULL,
    approved_at     TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    front_cover_path TEXT,
    chapter_image_path TEXT,
    back_cover_path TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id     TEXT NOT NULL,
    action       TEXT NOT NULL,
    reason_code  TEXT,
    note         TEXT NOT NULL DEFAULT '',
    reviewed_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id    INTEGER,
    project_id    INTEGER,
    type          TEXT NOT NULL,
    content       TEXT NOT NULL,
    image_prompt  TEXT,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_chapters_created ON chapters(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chapters_project ON chapters(project_id);
"""


def _connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(
        config.SQLITE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,  # autocommit
    )
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    
    # Migration: Add project_id and make chapter_id nullable
    try:
        # Check current columns and constraints
        table_info = conn.execute("PRAGMA table_info(posts)").fetchall()
        col_names = [row["name"] for row in table_info]
        chapter_id_info = next((row for row in table_info if row["name"] == "chapter_id"), None)
        
        # 1. If project_id is missing, add it simply
        if "project_id" not in col_names:
            conn.execute("ALTER TABLE posts ADD COLUMN project_id INTEGER")
            
        # 2. If chapter_id is NOT NULL, we MUST recreate the table
        if chapter_id_info and chapter_id_info["notnull"] == 1:
            # Recreate table using a temp table
            conn.execute("BEGIN TRANSACTION")
            try:
                conn.execute("CREATE TABLE posts_backup AS SELECT * FROM posts")
                conn.execute("DROP TABLE posts")
                conn.execute(_SCHEMA) # Re-create using the current _SCHEMA which allows NULL
                
                # Copy back data
                # We need to map columns since old table might not have project_id yet or schema differs
                old_cols = [row["name"] for row in conn.execute("PRAGMA table_info(posts_backup)").fetchall()]
                cols_to_copy = [c for c in old_cols if c in ["id", "chapter_id", "project_id", "type", "content", "image_prompt", "status", "created_at"]]
                cols_str = ", ".join(cols_to_copy)
                conn.execute(f"INSERT INTO posts ({cols_str}) SELECT {cols_str} FROM posts_backup")
                
                conn.execute("DROP TABLE posts_backup")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
                
        # Migration: Add asset paths to projects
        project_info = conn.execute("PRAGMA table_info(projects)").fetchall()
        p_cols = [row["name"] for row in project_info]
        if "front_cover_path" not in p_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN front_cover_path TEXT")
        if "chapter_image_path" not in p_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN chapter_image_path TEXT")
        if "back_cover_path" not in p_cols:
            conn.execute("ALTER TABLE projects ADD COLUMN back_cover_path TEXT")
            
    except sqlite3.OperationalError:
        pass # Table might not exist yet
    
    # Migration: Add cover_path to chapters
    try:
        conn.execute("ALTER TABLE chapters ADD COLUMN cover_path TEXT")
    except sqlite3.OperationalError:
        pass

    return conn


# === Chapter CRUD ===

def save_draft(draft: ChapterDraft) -> str:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chapters
                (topic, content_md, image_prompts, status, retry_count,
                 parent_id, reject_history, input_tokens, output_tokens,
                 project_id, cover_path, created_at, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft.topic,
                draft.content_md,
                json.dumps(draft.image_prompts, ensure_ascii=False),
                draft.status.value,
                draft.retry_count,
                int(draft.parent_id) if draft.parent_id else None,
                json.dumps(
                    [r.model_dump(mode="json") for r in draft.reject_history],
                    ensure_ascii=False,
                ),
                draft.input_tokens,
                draft.output_tokens,
                draft.project_id,
                draft.cover_path,
                draft.created_at.isoformat(),
                draft.approved_at.isoformat() if draft.approved_at else None,
            ),
        )
        return str(cur.lastrowid)


def get_draft(draft_id: str) -> ChapterDraft | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM chapters WHERE id = ?", (int(draft_id),)
        ).fetchone()
    if row is None:
        return None
    return _row_to_draft(row)


def list_by_status(status: ChapterStatus, limit: int = 50) -> list[tuple[str, ChapterDraft]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chapters WHERE status = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (status.value, limit),
        ).fetchall()
    return [(str(r["id"]), _row_to_draft(r)) for r in rows]


def update_draft(draft_id: str, updates: dict[str, Any]) -> None:
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE chapters SET {cols} WHERE id = ?",
            (*updates.values(), int(draft_id)),
        )


def approve_draft(draft_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE chapters SET status = ?, approved_at = ? WHERE id = ?",
            (ChapterStatus.APPROVED.value, datetime.now().isoformat(), int(draft_id)),
        )


def delete_draft(draft_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chapters WHERE id = ?", (int(draft_id),))


def set_status(draft_id: str, status: ChapterStatus) -> None:
    """Quick status transition — used by Approve-again / Un-approve actions."""
    with _connect() as conn:
        conn.execute(
            "UPDATE chapters SET status = ?, approved_at = ? WHERE id = ?",
            (
                status.value,
                datetime.now().isoformat() if status == ChapterStatus.APPROVED else None,
                int(draft_id),
            ),
        )


def reject_draft(draft_id: str, reject: RejectEntry) -> ChapterDraft:
    """Append reject entry. Status becomes REJECTED, or ESCALATED if MAX_RETRY hit."""
    draft = get_draft(draft_id)
    if draft is None:
        raise ValueError(f"Draft {draft_id} not found")

    draft.reject_history.append(reject)
    new_status = (
        ChapterStatus.ESCALATED
        if draft.retry_count >= config.MAX_RETRY
        else ChapterStatus.REJECTED
    )

    with _connect() as conn:
        conn.execute(
            "UPDATE chapters SET status = ?, reject_history = ? WHERE id = ?",
            (
                new_status.value,
                json.dumps(
                    [r.model_dump(mode="json") for r in draft.reject_history],
                    ensure_ascii=False,
                ),
                int(draft_id),
            ),
        )
    draft.status = new_status
    return draft


# === Approval log ===

def log_approval(record: ApprovalRecord) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO approvals (draft_id, action, reason_code, note, reviewed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.draft_id,
                record.action,
                record.reason_code.value if record.reason_code else None,
                record.note,
                record.reviewed_at.isoformat(),
            ),
        )


# === Post CRUD ===

def save_post(post: PostDraft) -> str:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO posts (chapter_id, project_id, type, content, image_prompt, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(post.chapter_id) if post.chapter_id else None,
                int(post.project_id) if post.project_id else None,
                post.type.value,
                post.content,
                post.image_prompt,
                post.status.value,
                post.created_at.isoformat(),
            ),
        )
        return str(cur.lastrowid)


def get_post(post_id: str) -> PostDraft | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (int(post_id),)).fetchone()
        if row is None:
            return None
        return PostDraft(
            chapter_id=str(row["chapter_id"]) if row["chapter_id"] else None,
            project_id=row["project_id"],
            type=PostType(row["type"]),
            content=row["content"],
            image_prompt=row["image_prompt"],
            status=PostStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def list_posts_by_chapter(chapter_id: str) -> list[tuple[str, PostDraft]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM posts WHERE chapter_id = ? ORDER BY created_at DESC",
            (int(chapter_id),),
        ).fetchall()
        return [(str(row["id"]), PostDraft(
            chapter_id=str(row["chapter_id"]),
            project_id=row["project_id"],
            type=PostType(row["type"]),
            content=row["content"],
            image_prompt=row["image_prompt"],
            status=PostStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )) for row in rows]


def list_posts_by_project(project_id: int) -> list[tuple[str, PostDraft]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM posts WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [(str(row["id"]), PostDraft(
            chapter_id=None,
            project_id=row["project_id"],
            type=PostType(row["type"]),
            content=row["content"],
            image_prompt=row["image_prompt"],
            status=PostStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )) for row in rows]


def list_all_posts(limit: int = 50) -> list[tuple[str, PostDraft]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [(str(row["id"]), PostDraft(
            chapter_id=str(row["chapter_id"]) if row["chapter_id"] else None,
            project_id=row["project_id"],
            type=PostType(row["type"]),
            content=row["content"],
            image_prompt=row["image_prompt"],
            status=PostStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )) for row in rows]


def approve_post(post_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET status = ? WHERE id = ?",
            (PostStatus.APPROVED.value, int(post_id)),
        )


def update_post_content(post_id: str, new_content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET content = ? WHERE id = ?",
            (new_content, int(post_id)),
        )


def delete_post(post_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (int(post_id),))


# === Project CRUD ===

def save_project(project: Project) -> str:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO projects 
                (name, description, front_cover_path, chapter_image_path, back_cover_path, created_at) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project.name, 
                project.description,
                project.front_cover_path,
                project.chapter_image_path,
                project.back_cover_path,
                project.created_at.isoformat()
            ),
        )
        return str(cur.lastrowid)


def list_projects() -> list[tuple[str, Project]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [(str(r["id"]), Project(
        name=r["name"],
        description=r["description"],
        front_cover_path=r["front_cover_path"],
        chapter_image_path=r["chapter_image_path"],
        back_cover_path=r["back_cover_path"],
        created_at=datetime.fromisoformat(r["created_at"])
    )) for r in rows]


def get_project(project_id: str) -> Project | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (int(project_id),)).fetchone()
    if row is None:
        return None
    return Project(
        name=row["name"],
        description=row["description"],
        front_cover_path=row["front_cover_path"],
        chapter_image_path=row["chapter_image_path"],
        back_cover_path=row["back_cover_path"],
        created_at=datetime.fromisoformat(row["created_at"])
    )


def update_project_assets(project_id: str, updates: dict[str, Any]) -> None:
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    with _connect() as conn:
        conn.execute(
            f"UPDATE projects SET {cols} WHERE id = ?",
            (*updates.values(), int(project_id)),
        )


def delete_project(project_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (int(project_id),))


def assign_chapter_to_project(chapter_id: str, project_id: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE chapters SET project_id = ? WHERE id = ?",
            (int(project_id) if project_id else None, int(chapter_id)),
        )


def list_chapters_by_project(project_id: str | None) -> list[tuple[str, ChapterDraft]]:
    with _connect() as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE project_id = ? ORDER BY created_at ASC",
                (int(project_id),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chapters WHERE project_id IS NULL ORDER BY created_at ASC"
            ).fetchall()
    return [(str(r["id"]), _row_to_draft(r)) for r in rows]


def update_draft_content(draft_id: str, new_topic: str, new_content_md: str, new_image_prompts: list[str] = None) -> None:
    """Directly overwrite a chapter's topic and content_md (used by the in-app editor)."""
    with _connect() as conn:
        if new_image_prompts is not None:
            import json
            conn.execute(
                "UPDATE chapters SET topic = ?, content_md = ?, image_prompts = ? WHERE id = ?",
                (new_topic, new_content_md, json.dumps(new_image_prompts), int(draft_id)),
            )
        else:
            conn.execute(
                "UPDATE chapters SET topic = ?, content_md = ? WHERE id = ?",
                (new_topic, new_content_md, int(draft_id)),
            )


def update_chapter_cover(chapter_id: str, cover_path: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE chapters SET cover_path = ? WHERE id = ?",
            (cover_path, int(chapter_id)),
        )


# === Helpers ===

def _row_to_post(row: sqlite3.Row) -> PostDraft:
    return PostDraft(
        chapter_id=str(row["chapter_id"]),
        type=PostType(row["type"]),
        content=row["content"],
        image_prompt=row["image_prompt"],
        status=PostStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_draft(row: sqlite3.Row) -> ChapterDraft:
    reject_history_raw = json.loads(row["reject_history"])
    reject_history = [
        RejectEntry(
            reason_code=RejectReason(item["reason_code"]),
            note=item.get("note", ""),
            at=datetime.fromisoformat(item["at"]),
        )
        for item in reject_history_raw
    ]
    return ChapterDraft(
        topic=row["topic"],
        content_md=row["content_md"],
        image_prompts=json.loads(row["image_prompts"]),
        status=ChapterStatus(row["status"]),
        retry_count=row["retry_count"],
        parent_id=str(row["parent_id"]) if row["parent_id"] else None,
        reject_history=reject_history,
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        project_id=row["project_id"],
        cover_path=row["cover_path"],
        created_at=datetime.fromisoformat(row["created_at"]),
        approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
    )


def approve_post(post_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET status = ? WHERE id = ?",
            (PostStatus.APPROVED.value, int(post_id)),
        )


def delete_post(post_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM posts WHERE id = ?", (int(post_id),))


def update_post_content(post_id: str, new_content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE posts SET content = ? WHERE id = ?",
            (new_content, int(post_id)),
        )
