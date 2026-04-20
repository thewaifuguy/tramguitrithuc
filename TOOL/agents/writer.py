"""WriterAgent: generate (and regenerate) one handbook chapter in markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass

import config
from agents.base import BaseAgent
from db.schemas import REJECT_REASON_LABELS, RejectEntry


@dataclass
class WriterOutput:
    topic: str
    content_md: str
    image_prompts: list[str]
    input_tokens: int
    output_tokens: int


class WriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            model=config.WRITER_MODEL,
            system_prompt_path=config.PROMPTS_DIR / "writer_system.md",
            temperature=config.WRITER_TEMPERATURE,
            max_tokens=config.WRITER_MAX_TOKENS,
        )
        self._regenerate_template = (
            config.PROMPTS_DIR / "regenerate.md"
        ).read_text(encoding="utf-8")

    def generate_chapter(self, topic: str, outline: str | None = None) -> WriterOutput:
        user_prompt = self._build_fresh_prompt(topic, outline)
        return self._run(topic, user_prompt)

    def regenerate_chapter(
        self,
        topic: str,
        previous_content: str,
        reject: RejectEntry,
    ) -> WriterOutput:
        user_prompt = self._build_regenerate_prompt(topic, previous_content, reject)
        return self._run(topic, user_prompt)

    def _run(self, topic: str, user_prompt: str) -> WriterOutput:
        response = self.complete(user_prompt)
        return WriterOutput(
            topic=topic,
            content_md=response.content,
            image_prompts=self._extract_image_prompts(response.content),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )

    def _build_fresh_prompt(self, topic: str, outline: str | None) -> str:
        lines = [f"Chủ đề của chapter: **{topic}**"]
        if outline:
            lines.append(f"\nOutline gợi ý:\n{outline}")
        lines.append(
            "\nHãy viết 1 chapter hoàn chỉnh theo đúng cấu trúc và yêu cầu trong "
            "system prompt. Nhớ chèn 2-4 tag `<!-- IMAGE_PROMPT: ... -->` trong "
            "nội dung tại chỗ phù hợp."
        )
        return "\n".join(lines)

    def _build_regenerate_prompt(
        self,
        topic: str,
        previous_content: str,
        reject: RejectEntry,
    ) -> str:
        fresh = self._build_fresh_prompt(topic, outline=None)
        reason_label = REJECT_REASON_LABELS.get(reject.reason_code, reject.reason_code.value)
        feedback = self._regenerate_template.format(
            reason_code=reject.reason_code.value,
            reason_label=reason_label,
            note=reject.note or "(reviewer không ghi chú thêm)",
            previous_content=previous_content,
        )
        return f"{fresh}\n\n---\n\n{feedback}"

    @staticmethod
    def _extract_image_prompts(content: str) -> list[str]:
        pattern = r"<!--\s*IMAGE_PROMPT:\s*(.+?)\s*-->"
        return re.findall(pattern, content, flags=re.DOTALL)
