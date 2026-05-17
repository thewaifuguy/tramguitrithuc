"""Pydantic models for Firestore collections."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ChapterStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"  # after MAX_RETRY rejects


class RejectReason(str, Enum):
    TOO_GENERIC = "too_generic"          # Wikipedia-style, không có cá tính
    TOO_LONG = "too_long"                # dài lan man
    TOO_SHORT = "too_short"              # thiếu chi tiết
    WRONG_TONE = "wrong_tone"            # giọng văn sai đối tượng
    FACTUAL_ERROR = "factual_error"      # sai thông tin/bịa
    MISSING_EXAMPLES = "missing_examples"  # thiếu ví dụ cụ thể VN
    BORING_HOOK = "boring_hook"          # mở bài chán, cliché
    BAD_STRUCTURE = "bad_structure"      # sai cấu trúc heading
    UNNATURAL_IMAGE = "unnatural_image"  # ảnh lỗi AI, sai giải phẫu
    OTHER = "other"                       # kèm note bắt buộc


REJECT_REASON_LABELS = {
    RejectReason.TOO_GENERIC: "Quá generic (như Wikipedia)",
    RejectReason.TOO_LONG: "Quá dài, lan man",
    RejectReason.TOO_SHORT: "Quá ngắn, thiếu chi tiết",
    RejectReason.WRONG_TONE: "Giọng văn không phù hợp",
    RejectReason.FACTUAL_ERROR: "Sai thông tin / bịa dữ liệu",
    RejectReason.MISSING_EXAMPLES: "Thiếu ví dụ cụ thể VN",
    RejectReason.BORING_HOOK: "Mở bài chán, cliché",
    RejectReason.BAD_STRUCTURE: "Sai cấu trúc heading",
    RejectReason.UNNATURAL_IMAGE: "Ảnh không tự nhiên (lỗi AI, sai giải phẫu)",
    RejectReason.OTHER: "Lý do khác (ghi chú bên dưới)",
}


class RejectEntry(BaseModel):
    reason_code: RejectReason
    note: str = ""
    at: datetime = Field(default_factory=datetime.now)


class ChapterDraft(BaseModel):
    topic: str
    content_md: str
    image_prompts: list[str] = Field(default_factory=list)
    status: ChapterStatus = ChapterStatus.PENDING
    retry_count: int = 0
    parent_id: str | None = None  # points to previous draft if this is a regenerate
    reject_history: list[RejectEntry] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    project_id: int | None = None  # Link to a project
    cover_path: str | None = None  # Chapter-specific transition image
    created_at: datetime = Field(default_factory=datetime.now)
    approved_at: datetime | None = None


class ApprovalRecord(BaseModel):
    draft_id: str
    action: str  # "approve" | "reject"
    reason_code: RejectReason | None = None
    note: str = ""
    reviewed_at: datetime = Field(default_factory=datetime.now)


class PostType(str, Enum):
    CAROUSEL = "carousel"
    SHORT = "short"
    REEL = "reel"
    INFORMATIVE = "informative"
    PROMO = "promo"


class PostStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"


class PostDraft(BaseModel):
    chapter_id: str | None = None  # Optional if it's a project promo
    project_id: int | None = None  # Link to project for PROMO posts
    type: PostType
    content: str
    image_prompt: str | None = None
    status: PostStatus = PostStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)


class Project(BaseModel):
    name: str
    description: str = ""
    front_cover_path: str | None = None
    chapter_image_path: str | None = None
    back_cover_path: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
