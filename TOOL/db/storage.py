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
    created_at      TEXT NOT NULL,
    approved_at     TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id     TEXT NOT NULL,
    action       TEXT NOT NULL,
    reason_code  TEXT,
    note         TEXT NOT NULL DEFAULT '',
    reviewed_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chapters_status ON chapters(status);
CREATE INDEX IF NOT EXISTS idx_chapters_created ON chapters(created_at DESC);
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
    return conn


# === Chapter CRUD ===

def save_draft(draft: ChapterDraft) -> str:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chapters
                (topic, content_md, image_prompts, status, retry_count,
                 parent_id, reject_history, input_tokens, output_tokens,
                 created_at, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        if draft.retry_count + 1 >= config.MAX_RETRY
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


# === Helpers ===

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
        created_at=datetime.fromisoformat(row["created_at"]),
        approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
    )
