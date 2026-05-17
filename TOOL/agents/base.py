"""BaseAgent: thin wrapper around LiteLLM with logging + retry on rate limit."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from litellm import completion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

import config

# Errors worth catching — some retry, some hard-fail
_CATCHABLE = (
    RateLimitError,
    ServiceUnavailableError,
    InternalServerError,
    APIConnectionError,
    Timeout,
    APIError,
    BadRequestError,  # Gemini 429 quota sometimes comes as BadRequestError
)


@dataclass
class AgentResponse:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class BaseAgent:
    def __init__(
        self,
        model: str,
        system_prompt_path: Path | str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = Path(system_prompt_path).read_text(encoding="utf-8")

    def complete(self, user_prompt: str, retries: int = 4) -> AgentResponse:
        config.require_gemini_key()

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=config.GEMINI_API_KEY,
                    request_timeout=60, # 60s timeout for safety
                )
                usage = response.usage
                return AgentResponse(
                    content=response.choices[0].message.content,
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                    model=self.model,
                )
            except _CATCHABLE as e:
                last_error = e
                # Daily quota hit → không retry (chỉ tốn thêm quota)
                if _is_daily_quota_error(e):
                    raise RuntimeError(
                        f"Hết quota daily của Gemini free tier cho model "
                        f"`{self.model}`.\n\n"
                        f"Google đã giảm free tier xuống rất thấp (20 req/ngày cho 2.5-flash).\n\n"
                        f"**Giải pháp:**\n"
                        f"• Đổi sang model khác trong `config.py` (VD: gemini-2.0-flash-lite, gemini-2.5-flash-lite)\n"
                        f"• Tạo API key mới từ Google account khác\n"
                        f"• Enable billing ở aistudio.google.com"
                    ) from e
                # Nếu là BadRequestError nhưng KHÔNG phải quota → không retry
                if isinstance(e, BadRequestError):
                    raise RuntimeError(
                        f"Lỗi từ Gemini API (BadRequest): {e}\n\n"
                        f"Kiểm tra model name trong config.py hoặc nội dung prompt."
                    ) from e
                # Transient → backoff retry
                wait = 4 * (2 ** attempt)
                kind = type(e).__name__
                print(f"[{kind}] retry {attempt + 1}/{retries} after {wait}s...")
                time.sleep(wait)

        raise RuntimeError(
            f"Gemini API tạm thời không phản hồi sau {retries} lần thử "
            f"({type(last_error).__name__}). Thử lại sau vài phút nhé."
        )


def _is_daily_quota_error(e: Exception) -> bool:
    """Distinguish daily quota (hard stop) vs per-minute burst (retryable)."""
    msg = str(e).lower()
    return "perday" in msg or "per day" in msg or "requestsperdayperproject" in msg
